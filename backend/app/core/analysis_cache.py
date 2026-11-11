import hashlib
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from time import time
from urllib.parse import unquote, unquote_plus

from pydantic import ValidationError

from app.core.config import settings
from app.prompts.gemini_prompts import ASSESS_PROMPT, EXTRACT_CLAIMS_PROMPT
from app.schemas.response import AnalyzeResponse

PROMPT_VERSION = hashlib.sha256(
    f"{EXTRACT_CLAIMS_PROMPT}\0{ASSESS_PROMPT}".encode()
).hexdigest()
HIGH_CONFIDENCE = 0.8


def normalize_cache_text(text: str) -> str:
    return " ".join(text.lower().split())


@dataclass(frozen=True)
class CacheKey:
    content_hash: str
    prompt_version: str
    model_id: str
    lang_hash: str

    @classmethod
    def for_request(cls, text: str, model_id: str, lang: str | None) -> "CacheKey":
        digest = hashlib.sha256(normalize_cache_text(text).encode("utf-8")).hexdigest()
        # Lang do client cung cấp và chỉ dùng để phân vùng cache.
        lang_hash = hashlib.sha256((lang or "").encode("utf-8")).hexdigest()
        return cls(digest, PROMPT_VERSION, model_id, lang_hash)

    def sql_params(self) -> tuple[str, str, str, str]:
        return self.content_hash, self.prompt_version, self.model_id, self.lang_hash


def _string_values(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _string_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _string_values(child)


def _contains_request_content(
    response: AnalyzeResponse, text: str, page_url: str | None
) -> bool:
    # Lời giải thích hoặc dữ liệu nguồn có thể lặp lại nguyên văn đầu vào.
    sensitive = {
        value for raw in (text, page_url) if raw if (value := normalize_cache_text(raw))
    }
    for value in _string_values(response.model_dump(mode="json")):
        candidates = (value, unescape(unquote(value)), unescape(unquote_plus(value)))
        if any(
            secret in normalize_cache_text(candidate)
            for candidate in candidates
            for secret in sensitive
        ):
            return True
    return False


class AnalysisCache:
    def __init__(self, path: Path):
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=0.05)

    def initialize(self) -> None:
        with closing(sqlite3.connect(self.path, timeout=1.0)) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    content_hash TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    lang TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (content_hash, prompt_version, model_id, lang)
                );
                CREATE INDEX IF NOT EXISTS analysis_cache_expiry
                    ON analysis_cache(expires_at);
            """)
            db.execute("DELETE FROM analysis_cache WHERE expires_at <= ?", (time(),))

    def get(self, key: CacheKey) -> AnalyzeResponse | None:
        with closing(self._connect()) as db:
            row = db.execute(
                """
                SELECT payload FROM analysis_cache
                WHERE content_hash = ? AND prompt_version = ?
                    AND model_id = ? AND lang = ? AND expires_at > ?
                """,
                (*key.sql_params(), time()),
            ).fetchone()
        if row is None:
            return None
        try:
            return AnalyzeResponse.model_validate_json(row[0])
        except ValidationError:
            return None

    def save(
        self,
        key: CacheKey,
        result: AnalyzeResponse,
        *,
        text: str,
        page_url: str | None,
        timed_out: bool,
    ) -> None:
        if timed_out or "error" in result.service_status.model_dump().values():
            return
        if result.verdict == "unverified":
            ttl = settings.cache_unverified_ttl_seconds
        elif result.confidence_score >= HIGH_CONFIDENCE:
            ttl = settings.cache_high_confidence_ttl_seconds
        else:
            ttl = settings.cache_low_confidence_ttl_seconds
        if ttl <= 0 or _contains_request_content(result, text, page_url):
            return

        now = time()
        payload = result.model_dump_json(exclude={"request_id"})
        with closing(self._connect()) as db, db:
            db.execute("DELETE FROM analysis_cache WHERE expires_at <= ?", (now,))
            db.execute(
                """
                INSERT INTO analysis_cache (
                    content_hash, prompt_version, model_id, lang, expires_at, payload
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (content_hash, prompt_version, model_id, lang)
                DO UPDATE SET expires_at = excluded.expires_at, payload = excluded.payload
                """,
                (*key.sql_params(), now + ttl, payload),
            )
