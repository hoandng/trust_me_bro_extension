import hashlib
import json
import sqlite3
from contextlib import closing
from time import perf_counter
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import quote

import httpx
import pytest
import respx
from app.api.deps import get_orchestrator
from app.core import analysis_cache
from app.core.config import settings
from app.core.metrics import current_metrics
from app.core.rate_limit import RateLimiter
from app.main import app
from app.schemas.response import AnalyzeResponse, ServiceStatus, Source
from app.services.gemini_model_pool import GeminiModelPool, GeminiQuotaExhausted
from fastapi.testclient import TestClient

HEADERS = {"X-API-Key": "cache-test-key"}
TEXT = "  PRIVATE   SYNTHETIC post for cache test.  "
NORMALIZED_TEXT = "private synthetic post for cache test."
PAGE_URL = "https://example.com/private-post?case=cache"
FACTCHECK_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
TAVILY_URL = "https://api.tavily.com/search"


@pytest.fixture
def limiter(monkeypatch):
    limiter = RateLimiter()
    monkeypatch.setattr("app.core.rate_limit.limiter", limiter)
    return limiter


@pytest.fixture
def sdk(monkeypatch):
    sdk = MagicMock()
    sdk.aio.interactions.create = AsyncMock(
        side_effect=AssertionError("Unexpected SDK call")
    )
    sdk.aio.aclose = AsyncMock()
    monkeypatch.setattr(
        "app.services.gemini_service.genai.Client", lambda **kwargs: sdk
    )
    monkeypatch.setattr("app.services.gemini_service.model_pool", GeminiModelPool())
    return sdk


@pytest.fixture
def client(monkeypatch, limiter, sdk):
    monkeypatch.setattr(settings, "extension_api_key", HEADERS["X-API-Key"])
    monkeypatch.setattr(settings, "gemini_api_key", "fake")
    monkeypatch.setattr(settings, "gemini_model", "gemini-cache-test")
    monkeypatch.setattr(settings, "gemini_models", ["gemini-cache-alt"])
    monkeypatch.setattr(settings, "tavily_api_key", "fake")
    monkeypatch.setattr(settings, "factcheck_api_key", "fake")
    monkeypatch.setattr(settings, "rate_limit_per_minute_ip", 50)
    monkeypatch.setattr(settings, "rate_limit_per_day_key", 100)
    monkeypatch.setattr(settings, "daily_analyze_limit_global", 100)
    monkeypatch.setattr(settings, "cache_high_confidence_ttl_seconds", 86400)
    monkeypatch.setattr(settings, "cache_low_confidence_ttl_seconds", 3600)
    monkeypatch.setattr(settings, "cache_unverified_ttl_seconds", 900)
    with TestClient(app) as client:
        yield client


def post(client, **overrides):
    return client.post(
        "/api/v1/analyze",
        headers=HEADERS,
        json={"text": TEXT, "platform": "reddit", "page_url": PAGE_URL, **overrides},
    )


def cache_rows(path):
    with closing(sqlite3.connect(path)) as db:
        db.row_factory = sqlite3.Row
        return db.execute("SELECT * FROM analysis_cache").fetchall()


@pytest.fixture
def pipeline(monkeypatch):
    pipeline = AsyncMock()
    monkeypatch.setitem(
        app.dependency_overrides,
        get_orchestrator,
        lambda: SimpleNamespace(analyze=pipeline),
    )
    return pipeline


def answer(**overrides):
    return AnalyzeResponse.model_validate(
        {
            "verdict": "likely_true",
            "confidence_score": 0.9,
            "explanation": "Có nguồn đối chứng.",
            "sources": [],
            "service_status": ServiceStatus(
                gemini="ok", factcheck="empty", tavily="ok"
            ),
            **overrides,
        }
    )


def test_hit_is_fast_has_new_uuid_skips_providers_and_key_quota(
    client, sdk, limiter, monkeypatch, metrics_db_path
):
    monkeypatch.setattr(settings, "rate_limit_per_day_key", 1)
    monkeypatch.setattr(settings, "rate_limit_per_minute_ip", 3)
    sdk.aio.interactions.create.side_effect = [
        SimpleNamespace(
            output_text=json.dumps(
                {
                    "main_claim": "Synthetic checkable claim",
                    "search_queries": ["synthetic query"],
                    "detected_lang": "en",
                    "is_checkable": True,
                }
            )
        ),
        SimpleNamespace(
            output_text=json.dumps(
                {
                    "verdict": "likely_true",
                    "confidence_score": 0.9,
                    "explanation": "Có nguồn đối chứng.",
                    "source_stances": [],
                }
            )
        ),
    ]
    with respx.mock(assert_all_mocked=True, assert_all_called=True) as router:
        factcheck = router.get(FACTCHECK_URL).mock(
            return_value=httpx.Response(200, json={"claims": []})
        )
        tavily = router.post(TAVILY_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {"title": "Nguồn mẫu", "url": "https://reuters.com/example"}
                    ],
                    "usage": {"credits": 1},
                },
            )
        )
        miss = post(client)
        assert miss.status_code == 200
        started = perf_counter()
        hit = post(client, text=NORMALIZED_TEXT)
        elapsed_ms = (perf_counter() - started) * 1000
        print(f"Cache hit via TestClient: {elapsed_ms:.1f} ms")
        assert hit.status_code == 200
        assert elapsed_ms < 300
        assert sdk.aio.interactions.create.await_count == 2
        assert tavily.call_count == 1
        assert factcheck.call_count == 2

        blocked_miss = post(client, text="Different synthetic text for quota test.")
        assert blocked_miss.status_code == 429
        assert "Key Quota" in blocked_miss.json()["detail"]
        blocked_hit = post(client)
        assert blocked_hit.status_code == 429
        assert blocked_hit.json()["detail"] == "Too Many Requests"

    first = miss.json()
    second = hit.json()
    assert first.pop("request_id") != second.pop("request_id")
    assert first == second
    assert len(limiter.key_records[HEADERS["X-API-Key"]]) == 1
    assert limiter.global_daily_count == 2
    with closing(sqlite3.connect(metrics_db_path)) as db:
        stats = db.execute(
            """SELECT cache_hit, tavily_calls, factcheck_calls, gemini_usage, estimated_cost_usd,
                      extract_ms, evidence_ms, assess_ms FROM analysis_metrics ORDER BY rowid"""
        ).fetchall()
    assert stats[0][:3] == (0, 1, 2)
    assert stats[1] == (1, 0, 0, "[]", 0.0, None, None, None)
    (cached,) = cache_rows(metrics_db_path)
    assert (
        cached["content_hash"] == hashlib.sha256(NORMALIZED_TEXT.encode()).hexdigest()
    )
    assert "request_id" not in json.loads(cached["payload"])
    assert NORMALIZED_TEXT not in cached["payload"].lower()
    assert PAGE_URL not in cached["payload"]


@pytest.mark.parametrize(
    ("verdict", "confidence", "ttl_setting", "default_ttl"),
    [
        ("likely_true", 0.8, "cache_high_confidence_ttl_seconds", 86400),
        ("mixed", 0.79, "cache_low_confidence_ttl_seconds", 3600),
        ("unverified", 0.9, "cache_unverified_ttl_seconds", 900),
    ],
)
def test_ttl_uses_verdict_confidence_and_settings(
    client,
    pipeline,
    monkeypatch,
    metrics_db_path,
    verdict,
    confidence,
    ttl_setting,
    default_ttl,
):
    now = 1000
    monkeypatch.setattr(analysis_cache, "time", lambda: now)
    assert type(settings).model_fields[ttl_setting].default == default_ttl
    monkeypatch.setattr(settings, ttl_setting, 10)
    pipeline.side_effect = lambda *args, **kwargs: answer(
        verdict=verdict, confidence_score=confidence
    )

    assert post(client).status_code == 200
    assert cache_rows(metrics_db_path)[0]["expires_at"] == 1010
    now = 1009
    assert post(client).status_code == 200
    assert pipeline.await_count == 1
    now = 1010
    assert post(client).status_code == 200
    assert pipeline.await_count == 2
    assert cache_rows(metrics_db_path)[0]["expires_at"] == 1020


@pytest.mark.parametrize(
    "failure", ["degraded", "timeout", "quota", "echo", "encoded_page_url"]
)
def test_does_not_cache_errors_or_request_content(
    client, pipeline, metrics_db_path, failure
):
    async def response(*args, **kwargs):
        if failure == "quota":
            raise GeminiQuotaExhausted(10)
        if failure == "degraded":
            return answer(
                service_status=ServiceStatus(
                    gemini="ok", factcheck="empty", tavily="error"
                )
            )
        if failure == "timeout":
            current_metrics.get().timed_out = True
            return answer(verdict="unverified", confidence_score=0.0)
        if failure == "echo":
            return answer(explanation="Nội dung được chọn: " + NORMALIZED_TEXT.upper())
        return answer(
            sources=[
                Source(
                    title="Nguồn mẫu",
                    url="https://example.com/redirect?q=" + quote(PAGE_URL, safe=""),
                ),
            ]
        )

    pipeline.side_effect = response
    expected_status = 503 if failure == "quota" else 200
    assert post(client).status_code == expected_status
    assert post(client).status_code == expected_status
    assert pipeline.await_count == 2
    assert cache_rows(metrics_db_path) == []
    assert NORMALIZED_TEXT.encode() not in metrics_db_path.read_bytes().lower()
    assert PAGE_URL.encode() not in metrics_db_path.read_bytes()


def test_bypass_skips_read_and_write(client, pipeline, metrics_db_path):
    pipeline.side_effect = [
        answer(explanation="Lượt bỏ qua cache khi chưa có kết quả"),
        answer(explanation="Kết quả được cache"),
        answer(explanation="Kết quả đo mới"),
    ]
    assert post(client, bypass_cache=True).status_code == 200
    assert cache_rows(metrics_db_path) == []
    assert post(client).json()["explanation"] == "Kết quả được cache"
    assert post(client, bypass_cache=True).json()["explanation"] == "Kết quả đo mới"
    assert post(client).json()["explanation"] == "Kết quả được cache"
    assert pipeline.await_count == 3


def test_cache_separates_prompt_versions_models_and_language(
    client, pipeline, monkeypatch, metrics_db_path
):
    pipeline.side_effect = lambda *args, **kwargs: answer()
    assert post(client).status_code == 200
    assert post(client).status_code == 200
    assert pipeline.await_count == 1
    assert post(client, model_id="gemini-cache-alt").status_code == 200
    assert post(client, lang="vi").status_code == 200
    monkeypatch.setattr(analysis_cache, "PROMPT_VERSION", "new-prompt-version")
    assert post(client).status_code == 200
    assert pipeline.await_count == 4
    assert len(cache_rows(metrics_db_path)) == 4
