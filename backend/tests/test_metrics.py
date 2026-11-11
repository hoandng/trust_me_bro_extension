import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import httpx
import pytest
import respx
from app.core.config import GeminiTokenPrices, settings
from app.core.metrics import AnalysisMetrics, GeminiUsage, content_digest
from app.core.rate_limit import RateLimiter
from app.main import app
from app.services.gemini_model_pool import GeminiModelPool
from fastapi.testclient import TestClient

EXTENSION_HEADERS = {"X-API-Key": "extension-test"}
ADMIN_HEADERS = {"X-Admin-API-Key": "admin-test"}
POST_TEXT = "  Thông tin  RIÊNG thử nghiệm B1.  "
PAGE_URL = "https://example.com/private-post?private=1"


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
def client(monkeypatch, sdk):
    monkeypatch.setattr(settings, "extension_api_key", EXTENSION_HEADERS["X-API-Key"])
    monkeypatch.setattr(settings, "admin_api_key", ADMIN_HEADERS["X-Admin-API-Key"])
    monkeypatch.setattr(settings, "gemini_api_key", "fake")
    monkeypatch.setattr(settings, "gemini_model", "gemini-metrics-test")
    monkeypatch.setattr(settings, "gemini_models", [])
    monkeypatch.setattr(settings, "tavily_api_key", "fake")
    monkeypatch.setattr(settings, "factcheck_api_key", "fake")
    monkeypatch.setattr(settings, "search_query_limit", 2)
    monkeypatch.setattr(settings, "rate_limit_per_minute_ip", 50)
    monkeypatch.setattr(settings, "rate_limit_per_day_key", 100)
    monkeypatch.setattr(settings, "daily_analyze_limit_global", 100)
    monkeypatch.setattr(
        settings,
        "gemini_token_prices",
        {
            "gemini-metrics-test": GeminiTokenPrices(
                input_usd_per_million=2,
                output_usd_per_million=4,
                cached_input_usd_per_million=1,
            )
        },
    )
    monkeypatch.setattr(settings, "tavily_usd_per_credit", 0.01)
    monkeypatch.setattr("app.core.rate_limit.limiter", RateLimiter())
    with TestClient(app) as test_client:
        yield test_client


def analyze(client):
    return client.post(
        "/api/v1/analyze",
        headers=EXTENSION_HEADERS,
        json={"text": POST_TEXT, "page_url": PAGE_URL, "platform": "reddit"},
    )


def rows(path):
    with closing(sqlite3.connect(path)) as db:
        db.row_factory = sqlite3.Row
        return db.execute(
            "SELECT * FROM analysis_metrics ORDER BY created_at"
        ).fetchall()


def interaction(output, usage):
    return SimpleNamespace(
        output_text=output if isinstance(output, str) else json.dumps(output),
        usage=SimpleNamespace(**usage),
    )


def test_records_metadata_and_actual_fallback_calls(
    client, sdk, metrics_db_path, caplog
):
    usage = {
        "total_input_tokens": 100,
        "total_output_tokens": 20,
        "total_thought_tokens": 5,
        "total_cached_tokens": 10,
        "total_tokens": 125,
    }
    sdk.aio.interactions.create.side_effect = [
        interaction("Invalid structured output", usage),
        interaction(
            {
                "main_claim": "Synthetic claim",
                "search_queries": ["first", "second", "ignored"],
                "detected_lang": "vi",
                "is_checkable": True,
            },
            usage,
        ),
        interaction(
            {
                "verdict": "mixed",
                "confidence_score": 0.6,
                "explanation": POST_TEXT + PAGE_URL,
                "source_stances": [],
            },
            usage,
        ),
    ]
    with respx.mock(assert_all_called=True) as router:
        factcheck = router.get(
            "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        ).mock(return_value=httpx.Response(200, json={"claims": []}))

        def tavily_response(request):
            payload = json.loads(request.content)
            assert payload["include_usage"] is True
            assert payload["query"] in {"first", "second"}
            results = (
                []
                if payload["topic"] == "news"
                else [
                    {
                        "title": "Synthetic source",
                        "url": "https://example.com/article",
                        "content": POST_TEXT,
                    }
                ]
            )
            return httpx.Response(
                200, json={"results": results, "usage": {"credits": 1}}
            )

        tavily = router.post("https://api.tavily.com/search").mock(
            side_effect=tavily_response
        )
        result = analyze(client)

    assert result.status_code == 200
    request_id = result.json()["request_id"]
    assert UUID(request_id).version == 4
    assert factcheck.call_count == tavily.call_count == 4
    (record,) = rows(metrics_db_path)
    assert record["request_id"] == request_id
    assert record["platform"] == "reddit"
    assert datetime.fromisoformat(record["created_at"]).utcoffset().total_seconds() == 0
    assert record["text_length"] == len(POST_TEXT)
    assert (
        record["content_hash"]
        == hashlib.sha256("Thông tin RIÊNG thử nghiệm B1.".encode()).hexdigest()
    )
    assert record["verdict"] == "mixed"
    assert record["confidence"] == pytest.approx(0.6)
    assert all(
        record[key] >= 0
        for key in ("extract_ms", "evidence_ms", "assess_ms", "total_ms")
    )
    assert (
        record["requested_model"]
        == record["extraction_model"]
        == record["assessment_model"]
        == "gemini-metrics-test"
    )
    assert (
        record["tavily_calls"]
        == record["factcheck_calls"]
        == record["tavily_credits"]
        == 4
    )
    gemini_usage = json.loads(record["gemini_usage"])
    assert [attempt["total_tokens"] for attempt in gemini_usage] == [125, 125, 125]
    assert all(
        call.kwargs["store"] is False
        for call in sdk.aio.interactions.create.await_args_list
    )
    assert record["cache_hit"] == 0
    assert record["estimated_cost_usd"] == pytest.approx(
        0.04 + 3 * (90 * 2 + 10 + 25 * 4) / 1_000_000
    )
    assert POST_TEXT.encode() not in metrics_db_path.read_bytes()
    assert PAGE_URL.encode() not in metrics_db_path.read_bytes()
    assert POST_TEXT not in caplog.text
    assert PAGE_URL not in caplog.text
    feedback = client.post(
        "/api/v1/feedback",
        headers=EXTENSION_HEADERS,
        json={
            "request_id": request_id,
            "helpful": True,
        },
    )
    assert feedback.status_code == 204
    summary = client.get("/api/v1/stats/summary", headers=ADMIN_HEADERS).json()
    assert summary["total_checks"] == 1
    assert summary["verdict_rates"]["mixed"] == 1
    assert (
        summary["average_latency_ms"] == summary["p95_latency_ms"] == record["total_ms"]
    )
    assert summary["cost_per_check_usd"] == pytest.approx(record["estimated_cost_usd"])
    assert summary["helpful_rate"] == 1


def test_summary_matches_known_data(client):
    store = app.state.metrics_store
    ids = [str(uuid4()) for _ in range(20)]
    latencies = [*range(10, 200, 10), 1000]
    for i, (request_id, latency) in enumerate(zip(ids, latencies, strict=True)):
        metrics = AnalysisMetrics(requested_model="gemini-metrics-test")
        if i < 2:
            metrics.tavily_credits = [i + 1]
        else:
            metrics.gemini_usage = [GeminiUsage(model="gemini-metrics-test")]
        store.record(
            request_id=request_id,
            created_at="2026-11-11T00:00:00+00:00",
            platform="reddit",
            text_length=25,
            content_hash=content_digest("Synthetic metadata fixture"),
            http_status=200 if i < 19 else 503,
            verdict="likely_true" if i < 10 else "mixed" if i < 19 else None,
            confidence=0.8 if i < 19 else None,
            total_ms=latency,
            metrics=metrics,
        )

    for index, helpful in ((0, False), (0, True), (1, False), (2, True)):
        response = client.post(
            "/api/v1/feedback",
            headers=EXTENSION_HEADERS,
            json={
                "request_id": ids[index],
                "helpful": helpful,
                "reason": "weak_sources" if not helpful else None,
            },
        )
        assert response.status_code == 204

    response = client.get("/api/v1/stats/summary", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    assert response.json() == {
        "total_checks": 20,
        "verdict_counts": {
            "likely_true": 10,
            "likely_false": 0,
            "mixed": 9,
            "unverified": 0,
        },
        "verdict_rates": {
            "likely_true": 10 / 19,
            "likely_false": 0,
            "mixed": 9 / 19,
            "unverified": 0,
        },
        "average_latency_ms": 145.0,
        "p95_latency_ms": 190,
        "cost_per_check_usd": pytest.approx(0.015),
        "checks_with_estimated_cost": 2,
        "feedback_count": 3,
        "helpful_rate": pytest.approx(2 / 3),
    }


def test_admin_auth_feedback_validation_and_shared_limits(client, monkeypatch, sdk):
    assert (
        client.get("/api/v1/stats/summary", headers=EXTENSION_HEADERS).status_code
        == 401
    )
    assert (
        client.get(
            "/api/v1/stats/summary", headers={"X-Admin-API-Key": "wrong"}
        ).status_code
        == 401
    )
    with monkeypatch.context() as disabled_admin:
        disabled_admin.setattr(settings, "admin_api_key", settings.extension_api_key)
        assert (
            client.get("/api/v1/stats/summary", headers=ADMIN_HEADERS).status_code
            == 503
        )

    summary = client.get("/api/v1/stats/summary", headers=ADMIN_HEADERS).json()
    assert summary["total_checks"] == 0
    assert (
        summary["p95_latency_ms"]
        is summary["helpful_rate"]
        is summary["cost_per_check_usd"]
        is None
    )

    payload = {"request_id": str(uuid4()), "helpful": False}
    assert client.post("/api/v1/feedback", json=payload).status_code == 401
    assert (
        client.post(
            "/api/v1/feedback", headers=EXTENSION_HEADERS, json=payload
        ).status_code
        == 404
    )
    for override in (
        {"helpful": "true"},
        {"reason": POST_TEXT},
        {"request_id": "invalid"},
        {"text": POST_TEXT},
    ):
        result = client.post(
            "/api/v1/feedback", headers=EXTENSION_HEADERS, json={**payload, **override}
        )
        assert result.status_code == 422
    monkeypatch.setattr(settings, "rate_limit_per_minute_ip", 6)
    sdk.aio.interactions.create.side_effect = None
    sdk.aio.interactions.create.return_value = interaction(
        {
            "main_claim": "",
            "search_queries": [],
            "detected_lang": "vi",
            "is_checkable": False,
        },
        {},
    )
    result = analyze(client)
    assert result.status_code == 200
    feedback = client.post(
        "/api/v1/feedback",
        headers=EXTENSION_HEADERS,
        json={
            **payload,
            "request_id": result.json()["request_id"],
        },
    )
    assert feedback.status_code == 429
    assert feedback.headers["Retry-After"]


def test_quota_failure_still_records_metadata(client, sdk, metrics_db_path):
    from google.genai.errors import APIError

    sdk.aio.interactions.create.side_effect = APIError(
        429, {"error": {"message": "Synthetic quota error"}}
    )
    result = analyze(client)
    assert result.status_code == 503
    assert result.headers["Retry-After"]
    (record,) = rows(metrics_db_path)
    assert record["http_status"] == 503
    assert (
        record["verdict"]
        is record["confidence"]
        is record["estimated_cost_usd"]
        is None
    )
    assert record["extract_ms"] >= 0
    assert record["evidence_ms"] is record["assess_ms"] is None
