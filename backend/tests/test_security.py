from ipaddress import ip_network

import pytest
from app.core.config import settings
from app.core.rate_limit import limiter
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_rate_limits(monkeypatch):
    # Reset limiter for tests
    limiter.ip_records.clear()
    limiter.key_records.clear()
    limiter.global_daily_count = 0
    monkeypatch.setattr(settings, "trust_proxy_headers", False)
    monkeypatch.setattr(settings, "extension_api_key", "test_key")
    monkeypatch.setattr(settings, "rate_limit_per_minute_ip", 2)
    monkeypatch.setattr(settings, "rate_limit_per_day_key", 3)
    monkeypatch.setattr(settings, "daily_analyze_limit_global", 5)
    monkeypatch.setattr(settings, "max_body_size_bytes", 1000)


def test_missing_api_key(client):
    response = client.post(
        "/api/v1/analyze", json={"text": "Hello", "platform": "facebook", "lang": "vi"}
    )
    assert response.status_code == 401


def test_rate_limit_ip(client):
    headers = {"X-API-Key": "test_key"}
    data = {"text": "Hello", "platform": "facebook", "lang": "vi"}

    # Request 1
    resp = client.post("/api/v1/analyze", json=data, headers=headers)
    assert resp.status_code != 429

    # Request 2
    resp = client.post("/api/v1/analyze", json=data, headers=headers)
    assert resp.status_code != 429

    # Request 3 - should fail IP limit
    resp = client.post("/api/v1/analyze", json=data, headers=headers)
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


def test_rate_limit_key(client):
    limiter.ip_records.clear()  # clear IP limit
    headers = {"X-API-Key": "test_key"}
    data = {
        "text": "Synthetic post for rate limit checks.",
        "platform": "facebook",
        "lang": "vi",
    }

    settings.rate_limit_per_minute_ip = 100  # relax IP limit

    # 3 requests allowed by key limit
    for _ in range(3):
        resp = client.post("/api/v1/analyze", json=data, headers=headers)
        assert resp.status_code != 429

    # 4th should fail
    resp = client.post("/api/v1/analyze", json=data, headers=headers)
    assert resp.status_code == 429
    assert "Key Quota Exceeded" in resp.json()["detail"]


def test_global_limit(client):
    limiter.ip_records.clear()
    limiter.key_records.clear()
    settings.rate_limit_per_minute_ip = 100
    settings.rate_limit_per_day_key = 100
    settings.daily_analyze_limit_global = 2

    headers = {"X-API-Key": "test_key"}
    data = {
        "text": "Synthetic post for global limit checks.",
        "platform": "facebook",
        "lang": "vi",
    }

    # 2 requests allowed
    client.post("/api/v1/analyze", json=data, headers=headers)
    client.post("/api/v1/analyze", json=data, headers=headers)

    # 3rd should fail globally
    resp = client.post("/api/v1/analyze", json=data, headers=headers)
    assert resp.status_code == 429
    assert "Global Daily Limit Exceeded" in resp.json()["detail"]


def test_body_too_large(client):
    settings.max_body_size_bytes = 50
    headers = {"X-API-Key": "test_key"}
    data = {
        "text": "This is a very long text that will exceed the fifty bytes limit setup for this test.",
        "platform": "facebook",
        "lang": "vi",
    }

    resp = client.post("/api/v1/analyze", json=data, headers=headers)
    assert resp.status_code == 413
    assert "Request body too large" in resp.json()["detail"]


@pytest.mark.parametrize(
    ("enabled", "peer", "forwarded", "expected"),
    [
        (False, "10.0.0.3", ["198.51.100.4"], "10.0.0.3"),
        (True, "203.0.113.9", ["198.51.100.4"], "203.0.113.9"),
        (True, "10.0.0.3", ["198.51.100.99, 198.51.100.4, 10.0.0.2"], "198.51.100.4"),
        (True, "10.0.0.3", ["198.51.100.99", "2001:0db8::4, 10.0.0.2"], "2001:db8::4"),
        (True, "10.0.0.3", ["::ffff:198.51.100.4"], "198.51.100.4"),
        (True, "10.0.0.3", ["198.51.100.4, invalid"], "10.0.0.3"),
        (True, "10.0.0.3", ["10.0.0.2"], "10.0.0.3"),
        (True, "10.0.0.3", [], "10.0.0.3"),
    ],
)
def test_proxy_rate_limit_uses_expected_ip(
    monkeypatch, enabled, peer, forwarded, expected
):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "trust_proxy_headers", enabled)
    monkeypatch.setattr(settings, "trusted_proxy_networks", [ip_network("10.0.0.0/29")])
    monkeypatch.setattr(settings, "rate_limit_per_minute_ip", 1)
    headers = [
        ("X-API-Key", "test_key"),
        *(("X-Forwarded-For", hop) for hop in forwarded),
    ]
    data = {
        "text": "Synthetic post with enough text to validate.",
        "platform": "reddit",
    }
    with TestClient(app, client=(peer, 12345)) as proxied_client:
        assert (
            proxied_client.post(
                "/api/v1/analyze", headers=headers, json=data
            ).status_code
            == 200
        )
        retry = proxied_client.post("/api/v1/analyze", headers=headers, json=data)
        assert retry.status_code == 429
        assert retry.headers["Retry-After"]
    assert set(limiter.ip_records) == {expected}
