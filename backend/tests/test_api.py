from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_analyze_endpoint_success():
    payload = {
        "text": "This is a valid text to analyze, it has more than twenty characters.",
        "platform": "facebook"
    }
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] == "likely_false"
    assert data["confidence_score"] == 0.85
    assert "explanation" in data
    assert len(data["sources"]) > 0
    assert data["service_status"]["factcheck"] == "ok"

def test_analyze_endpoint_text_too_short():
    payload = {
        "text": "Too short",
        "platform": "facebook"
    }
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "String should have at least 20 characters" in data["detail"][0]["msg"]

def test_analyze_endpoint_text_too_long():
    payload = {
        "text": "a" * 2001,
        "platform": "facebook"
    }
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "String should have at most 2000 characters" in data["detail"][0]["msg"]

def test_analyze_endpoint_invalid_platform():
    payload = {
        "text": "This is a valid text to analyze, it has more than twenty characters.",
        "platform": "instagram"
    }
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "Input should be 'facebook', 'x' or 'reddit'" in data["detail"][0]["msg"]
