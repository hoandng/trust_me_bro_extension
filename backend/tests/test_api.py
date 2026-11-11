import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from app.core.config import settings
from app.core.rate_limit import RateLimiter
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    with TestClient(app) as test_client:
        yield test_client


# Ensure extension_api_key is set for tests
settings.extension_api_key = "test_secret_key"


@pytest.mark.asyncio
async def test_lifespan_reuses_clients_and_isolates_concurrent_model_usage(monkeypatch):
    monkeypatch.setattr(settings, "extension_api_key", "test_secret_key")
    monkeypatch.setattr(settings, "gemini_api_key", "fake_key")
    monkeypatch.setattr(settings, "gemini_model", "gemini-test-a")
    monkeypatch.setattr(settings, "gemini_models", ["gemini-test-b"])
    monkeypatch.setattr("app.core.rate_limit.limiter", RateLimiter())
    both_started = asyncio.Event()
    models = []

    async def extract(*, model, **kwargs):
        models.append(model)
        if len(models) == 2:
            both_started.set()
        await both_started.wait()
        return MagicMock(
            output_text=json.dumps(
                {
                    "main_claim": "",
                    "search_queries": [],
                    "detected_lang": "vi",
                    "is_checkable": False,
                }
            )
        )

    sdk = MagicMock()
    sdk.aio.interactions.create = AsyncMock(side_effect=extract)
    sdk.aio.aclose = AsyncMock()
    sdk_factory = MagicMock(return_value=sdk)
    monkeypatch.setattr("app.services.gemini_service.genai.Client", sdk_factory)

    async with app.router.lifespan_context(app):
        shared_client = app.state.http_client
        orchestrator = app.state.orchestrator
        assert orchestrator.factcheck_service._client is shared_client
        assert orchestrator.tavily_service._client is shared_client
        await orchestrator.factcheck_service.aclose()
        assert not shared_client.is_closed

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as api:

            async def analyze(model_id):
                return await api.post(
                    "/api/v1/analyze",
                    headers={"X-API-Key": "test_secret_key"},
                    json={
                        "text": "Synthetic post for testing concurrent requests.",
                        "platform": "reddit",
                        "model_id": model_id,
                    },
                )

            requested = ["gemini-test-a", "gemini-test-b"]
            responses = await asyncio.wait_for(
                asyncio.gather(*(analyze(model_id) for model_id in requested)),
                timeout=2,
            )
        assert app.state.orchestrator is orchestrator
        assert not shared_client.is_closed
        sdk.aio.aclose.assert_not_awaited()
        assert sorted(models) == requested
        for response, model_id in zip(responses, requested, strict=True):
            assert response.status_code == 200
            usage = response.json()["model_usage"]
            assert usage["requested_model"] == usage["extraction_model"] == model_id
            assert usage["fallbacks"] == []

    sdk_factory.assert_called_once()
    sdk.aio.aclose.assert_awaited_once()
    sdk.close.assert_called_once()
    assert shared_client.is_closed
    assert not hasattr(app.state, "orchestrator")


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_endpoint_no_key(client):
    payload = {
        "text": "This is a valid text to analyze, it has more than twenty characters.",
        "platform": "facebook",
    }
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 401


def test_analyze_endpoint_wrong_key(client):
    payload = {
        "text": "This is a valid text to analyze, it has more than twenty characters.",
        "platform": "facebook",
    }
    headers = {"X-API-Key": "wrong_key"}
    response = client.post("/api/v1/analyze", json=payload, headers=headers)
    assert response.status_code == 401


def test_analyze_endpoint_success(client):
    payload = {
        "text": "This is a valid text to analyze, it has more than twenty characters.",
        "platform": "facebook",
    }
    headers = {"X-API-Key": "test_secret_key"}

    # We can mock the get_orchestrator dependency
    from app.api.deps import get_orchestrator
    from app.schemas.internal import AnalysisContext
    from app.schemas.response import AnalyzeResponse, ServiceStatus

    class MockOrchestrator:
        async def analyze(
            self, ctx: AnalysisContext, *, model_id=None
        ) -> AnalyzeResponse:
            return AnalyzeResponse(
                verdict="likely_false",
                confidence_score=0.85,
                explanation="Mock explanation",
                sources=[],
                service_status=ServiceStatus(factcheck="ok", tavily="ok", gemini="ok"),
            )

    app.dependency_overrides[get_orchestrator] = lambda: MockOrchestrator()

    response = client.post("/api/v1/analyze", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] == "likely_false"
    assert data["confidence_score"] == 0.85
    assert "explanation" in data
    assert data["service_status"]["factcheck"] == "ok"

    app.dependency_overrides.clear()


def test_analyze_endpoint_text_too_short(client):
    payload = {"text": "Too short", "platform": "facebook"}
    headers = {"X-API-Key": "test_secret_key"}
    response = client.post("/api/v1/analyze", json=payload, headers=headers)
    assert response.status_code == 422
    data = response.json()
    assert "String should have at least 20 characters" in data["detail"][0]["msg"]


def test_analyze_endpoint_text_too_long(client):
    payload = {"text": "a" * 2001, "platform": "facebook"}
    headers = {"X-API-Key": "test_secret_key"}
    response = client.post("/api/v1/analyze", json=payload, headers=headers)
    assert response.status_code == 422
    data = response.json()
    assert "String should have at most 2000 characters" in data["detail"][0]["msg"]


def test_analyze_endpoint_invalid_platform(client):
    payload = {
        "text": "This is a valid text to analyze, it has more than twenty characters.",
        "platform": "instagram",
    }
    headers = {"X-API-Key": "test_secret_key"}
    response = client.post("/api/v1/analyze", json=payload, headers=headers)
    assert response.status_code == 422
    data = response.json()
    assert "Input should be 'facebook', 'x' or 'reddit'" in data["detail"][0]["msg"]


def test_model_catalog_authentication_and_no_analysis_charge(client):
    from app.core.rate_limit import limiter

    before = limiter.global_daily_count
    assert client.get("/api/v1/models").status_code == 401
    response = client.get("/api/v1/models", headers={"X-API-Key": "test_secret_key"})
    assert response.status_code == 200
    assert response.json()["default_model"] == settings.gemini_model
    assert response.json()["models"] == settings.available_gemini_models
    assert limiter.global_daily_count == before


def test_disabled_model_rejected(client):
    response = client.post(
        "/api/v1/analyze",
        headers={"X-API-Key": "test_secret_key"},
        json={
            "text": "This claim has enough text for the validation.",
            "platform": "facebook",
            "model_id": "not-an-enabled-model",
        },
    )
    assert response.status_code == 422


def test_model_selection_metadata_and_all_models_exhausted(client):
    from app.api.deps import get_orchestrator
    from app.schemas.response import AnalyzeResponse, ModelUsage, ServiceStatus
    from app.services.gemini_model_pool import GeminiQuotaExhausted

    class FakeOrchestrator:
        exhausted = False

        async def analyze(self, ctx, *, model_id=None):
            if self.exhausted:
                raise GeminiQuotaExhausted(60)
            return AnalyzeResponse(
                verdict="unverified",
                confidence_score=0,
                explanation="Test",
                sources=[],
                service_status=ServiceStatus(
                    gemini="ok", tavily="empty", factcheck="empty"
                ),
                model_usage=ModelUsage(
                    requested_model=model_id or settings.gemini_model,
                    extraction_model=settings.gemini_model,
                ),
            )

    orchestrator = FakeOrchestrator()
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    payload = {
        "text": "This claim has enough text for the validation.",
        "platform": "facebook",
        "model_id": settings.gemini_model,
        "bypass_cache": True,
    }
    try:
        response = client.post(
            "/api/v1/analyze", headers={"X-API-Key": "test_secret_key"}, json=payload
        )
        assert response.status_code == 200
        assert (
            response.json()["model_usage"]["requested_model"] == settings.gemini_model
        )
        orchestrator.exhausted = True
        response = client.post(
            "/api/v1/analyze", headers={"X-API-Key": "test_secret_key"}, json=payload
        )
        assert response.status_code == 503
        assert response.headers["Retry-After"] == "60"
    finally:
        app.dependency_overrides.clear()
