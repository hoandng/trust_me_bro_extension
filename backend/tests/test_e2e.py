from unittest.mock import AsyncMock

import pytest
from app.api.deps import get_orchestrator
from app.core.config import settings
from app.main import app
from app.orchestrator.analysis_orchestrator import AnalysisOrchestrator
from app.schemas.internal import ServiceResult
from app.schemas.response import Source
from app.services.gemini_service import Assessment, ClaimExtraction
from fastapi.testclient import TestClient


@pytest.fixture
def mock_orchestrator():
    mock_gemini = AsyncMock()
    mock_factcheck = AsyncMock()
    mock_tavily = AsyncMock()

    # Mock gemini extract
    mock_gemini.extract_claims.return_value = ClaimExtraction(
        main_claim="This is a test claim.",
        search_queries=["test query"],
        is_checkable=True,
        detected_lang="vi",
    )

    # Mock gemini assess
    mock_gemini.assess.return_value = Assessment(
        verdict="likely_true",
        confidence_score=0.9,
        explanation="Test explanation.",
        source_stances=[],
        status="ok",
    )

    # Mock factcheck
    mock_factcheck.check.return_value = ServiceResult(
        service="factcheck",
        sources=[
            Source(
                url="https://test.factcheck",
                title="Test Fact",
                snippet="test snippet",
                stance="supports",
                domain="test.factcheck",
            )
        ],
        status="ok",
    )

    # Mock tavily
    mock_tavily.check.return_value = ServiceResult(
        service="tavily",
        sources=[
            Source(
                url="https://test.tavily",
                title="Test Search",
                snippet="test snippet",
                stance="neutral",
                domain="test.tavily",
            )
        ],
        status="ok",
    )

    return AnalysisOrchestrator(
        gemini_service=mock_gemini,
        factcheck_service=mock_factcheck,
        tavily_service=mock_tavily,
    )


@pytest.fixture
def client(mock_orchestrator, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    # We must also mock verify_api_key or pass it
    from app.api.deps import verify_api_key

    app.dependency_overrides[verify_api_key] = lambda: "test-api-key"

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.mark.e2e
def test_analyze_e2e(client):
    response = client.post(
        "/api/v1/analyze",
        json={
            "text": "This is a test claim. We need enough length.",
            "platform": "facebook",
            "lang": "vi",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] == "likely_true"
    assert data["confidence_score"] == 0.9
    assert data["explanation"] == "Test explanation."
    assert data["service_status"]["gemini"] == "ok"
    assert data["service_status"]["factcheck"] == "ok"
    assert data["service_status"]["tavily"] == "ok"
    assert len(data["sources"]) == 2
