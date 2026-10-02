import os
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app)

# Ensure extension_api_key is set for tests
settings.extension_api_key = "test_secret_key"

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_analyze_endpoint_no_key():
    payload = {
        "text": "This is a valid text to analyze, it has more than twenty characters.",
        "platform": "facebook"
    }
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 401

def test_analyze_endpoint_wrong_key():
    payload = {
        "text": "This is a valid text to analyze, it has more than twenty characters.",
        "platform": "facebook"
    }
    headers = {"X-API-Key": "wrong_key"}
    response = client.post("/api/v1/analyze", json=payload, headers=headers)
    assert response.status_code == 401

def test_analyze_endpoint_success():
    payload = {
        "text": "This is a valid text to analyze, it has more than twenty characters.",
        "platform": "facebook"
    }
    headers = {"X-API-Key": "test_secret_key"}
    
    # We can mock the get_orchestrator dependency
    from app.api.deps import get_orchestrator
    from app.schemas.response import AnalyzeResponse, ServiceStatus
    from app.schemas.internal import AnalysisContext
    
    class MockOrchestrator:
        async def analyze(self, ctx: AnalysisContext) -> AnalyzeResponse:
            return AnalyzeResponse(
                verdict="likely_false",
                confidence_score=0.85,
                explanation="Mock explanation",
                sources=[],
                service_status=ServiceStatus(factcheck="ok", tavily="ok", gemini="ok")
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

def test_analyze_endpoint_text_too_short():
    payload = {
        "text": "Too short",
        "platform": "facebook"
    }
    headers = {"X-API-Key": "test_secret_key"}
    response = client.post("/api/v1/analyze", json=payload, headers=headers)
    assert response.status_code == 422
    data = response.json()
    assert "String should have at least 20 characters" in data["detail"][0]["msg"]

def test_analyze_endpoint_text_too_long():
    payload = {
        "text": "a" * 2001,
        "platform": "facebook"
    }
    headers = {"X-API-Key": "test_secret_key"}
    response = client.post("/api/v1/analyze", json=payload, headers=headers)
    assert response.status_code == 422
    data = response.json()
    assert "String should have at most 2000 characters" in data["detail"][0]["msg"]

def test_analyze_endpoint_invalid_platform():
    payload = {
        "text": "This is a valid text to analyze, it has more than twenty characters.",
        "platform": "instagram"
    }
    headers = {"X-API-Key": "test_secret_key"}
    response = client.post("/api/v1/analyze", json=payload, headers=headers)
    assert response.status_code == 422
    data = response.json()
    assert "Input should be 'facebook', 'x' or 'reddit'" in data["detail"][0]["msg"]
