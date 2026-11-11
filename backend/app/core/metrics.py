"""Thu thập và lưu metadata cho mỗi lượt phân tích."""

import hashlib
import json
import sqlite3
import unicodedata
from contextlib import closing
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.core.config import settings

VERDICTS = ("likely_true", "likely_false", "mixed", "unverified")


def content_digest(text: str) -> str:
    normalized = " ".join(unicodedata.normalize("NFKC", text).split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _count(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


@dataclass
class GeminiUsage:
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    thought_tokens: int | None = None
    cached_tokens: int | None = None
    total_tokens: int | None = None

    def record(self, usage: object) -> None:
        self.input_tokens = _count(getattr(usage, "total_input_tokens", None))
        self.output_tokens = _count(getattr(usage, "total_output_tokens", None))
        self.thought_tokens = _count(getattr(usage, "total_thought_tokens", None))
        self.cached_tokens = _count(getattr(usage, "total_cached_tokens", None))
        self.total_tokens = _count(getattr(usage, "total_tokens", None))

    def estimated_cost(self) -> float | None:
        prices = settings.gemini_token_prices.get(self.model)
        if prices is None or self.input_tokens is None or self.output_tokens is None:
            return None
        cached = self.cached_tokens or 0
        if cached > self.input_tokens or (
            cached and prices.cached_input_usd_per_million is None
        ):
            return None
        return (
            (self.input_tokens - cached) * prices.input_usd_per_million
            + cached * (prices.cached_input_usd_per_million or 0)
            + (self.output_tokens + (self.thought_tokens or 0))
            * prices.output_usd_per_million
        ) / 1_000_000


@dataclass
class AnalysisMetrics:
    requested_model: str
    extraction_model: str | None = None
    assessment_model: str | None = None
    extract_ms: int | None = None
    evidence_ms: int | None = None
    assess_ms: int | None = None
    total_ms: int | None = None
    factcheck_calls: int = 0
    tavily_credits: list[int | None] = field(default_factory=list)
    gemini_usage: list[GeminiUsage] = field(default_factory=list)
    cache_hit: bool = False

    def estimated_cost(self) -> float | None:
        cost = 0.0
        for usage in self.gemini_usage:
            part = usage.estimated_cost()
            if part is None:
                return None
            cost += part
        for credits in self.tavily_credits:
            price = settings.tavily_usd_per_credit
            if credits is None or price is None:
                return None
            cost += credits * price
        return cost

    def record_tavily_credits(self, attempt: int, usage: object) -> None:
        if isinstance(usage, dict):
            self.tavily_credits[attempt] = _count(usage.get("credits"))


# Các task tra cứu song song kế thừa bộ đếm của chính request.
current_metrics: ContextVar[AnalysisMetrics | None] = ContextVar(
    "current_metrics", default=None
)


class MetricsStore:
    def __init__(self, path: Path):
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=1.0)
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS analysis_metrics (
                    request_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    text_length INTEGER NOT NULL,
                    content_hash TEXT NOT NULL,
                    http_status INTEGER NOT NULL,
                    verdict TEXT,
                    confidence REAL,
                    extract_ms INTEGER,
                    evidence_ms INTEGER,
                    assess_ms INTEGER,
                    total_ms INTEGER NOT NULL,
                    requested_model TEXT NOT NULL,
                    extraction_model TEXT,
                    assessment_model TEXT,
                    tavily_calls INTEGER NOT NULL,
                    factcheck_calls INTEGER NOT NULL,
                    tavily_credits INTEGER,
                    gemini_usage TEXT NOT NULL,
                    cache_hit INTEGER NOT NULL CHECK (cache_hit IN (0, 1)),
                    estimated_cost_usd REAL
                );
                CREATE INDEX IF NOT EXISTS analysis_metrics_latency
                    ON analysis_metrics(total_ms);
                CREATE TABLE IF NOT EXISTS feedback (
                    request_id TEXT PRIMARY KEY REFERENCES analysis_metrics(request_id),
                    helpful INTEGER NOT NULL CHECK (helpful IN (0, 1)),
                    reason TEXT
                );
            """)

    def record(
        self,
        *,
        request_id: str,
        created_at: str,
        platform: str,
        text_length: int,
        content_hash: str,
        http_status: int,
        verdict: str | None,
        confidence: float | None,
        total_ms: int,
        metrics: AnalysisMetrics,
    ) -> None:
        credits = metrics.tavily_credits
        with closing(self._connect()) as db, db:
            db.execute(
                """
                INSERT INTO analysis_metrics (
                    request_id, created_at, platform, text_length, content_hash,
                    http_status, verdict, confidence, extract_ms, evidence_ms,
                    assess_ms, total_ms, requested_model, extraction_model,
                    assessment_model, tavily_calls, factcheck_calls, tavily_credits,
                    gemini_usage, cache_hit, estimated_cost_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    created_at,
                    platform,
                    text_length,
                    content_hash,
                    http_status,
                    verdict,
                    confidence,
                    metrics.extract_ms,
                    metrics.evidence_ms,
                    metrics.assess_ms,
                    total_ms,
                    metrics.requested_model,
                    metrics.extraction_model,
                    metrics.assessment_model,
                    len(credits),
                    metrics.factcheck_calls,
                    None
                    if None in credits
                    else sum(credit for credit in credits if credit is not None),
                    json.dumps([asdict(usage) for usage in metrics.gemini_usage]),
                    int(metrics.cache_hit),
                    metrics.estimated_cost(),
                ),
            )

    def save_feedback(self, request_id: str, helpful: bool, reason: str | None) -> bool:
        with closing(self._connect()) as db, db:
            cursor = db.execute(
                """
                INSERT INTO feedback (request_id, helpful, reason)
                    SELECT request_id, ?, ? FROM analysis_metrics WHERE request_id = ?
                    AND verdict IS NOT NULL
                ON CONFLICT (request_id) DO UPDATE SET
                    helpful = excluded.helpful, reason = excluded.reason
                """,
                (int(helpful), reason, request_id),
            )
            return cursor.rowcount == 1

    def summary(self) -> dict:
        with closing(self._connect()) as db, db:
            db.execute("BEGIN")
            total, verdict_count, mean_ms, cost_mean, cost_count = db.execute(
                """
                SELECT COUNT(*), COUNT(verdict), AVG(total_ms),
                    AVG(estimated_cost_usd), COUNT(estimated_cost_usd)
                FROM analysis_metrics
                """
            ).fetchone()
            verdicts = dict(
                db.execute(
                    "SELECT verdict, COUNT(*) FROM analysis_metrics WHERE verdict IS NOT NULL GROUP BY verdict"
                )
            )
            p95 = None
            if total:
                rank = (95 * total + 99) // 100
                (p95,) = db.execute(
                    "SELECT total_ms FROM analysis_metrics ORDER BY total_ms LIMIT 1 OFFSET ?",
                    (rank - 1,),
                ).fetchone()
            feedback_count, helpful_rate = db.execute(
                "SELECT COUNT(*), AVG(helpful) FROM feedback"
            ).fetchone()
        return {
            "total_checks": total,
            "verdict_counts": {
                verdict: verdicts.get(verdict, 0) for verdict in VERDICTS
            },
            "verdict_rates": {
                verdict: verdicts.get(verdict, 0) / verdict_count
                if verdict_count
                else 0.0
                for verdict in VERDICTS
            },
            "average_latency_ms": mean_ms,
            "p95_latency_ms": p95,
            "cost_per_check_usd": cost_mean,
            "checks_with_estimated_cost": cost_count,
            "feedback_count": feedback_count,
            "helpful_rate": helpful_rate,
        }
