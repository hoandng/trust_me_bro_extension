import httpx
import pytest
import respx
from app.core.config import settings
from app.schemas.internal import AnalysisContext
from app.services.factcheck_service import FactCheckService


@pytest.mark.parametrize(
    "rating, expected",
    [
        ("Not true", "refutes"),
        ("not accurate", "refutes"),
        ("True", "supports"),
        ("False", "refutes"),
        ("Untrue", "refutes"),
        ("Mostly True", "supports"),
        ("Mostly False", "refutes"),
        ("half-true", "neutral"),
        ("partly true", "neutral"),
        ("partly false", "neutral"),
        ("half false", "neutral"),
        ("sai sự thật", "refutes"),
        ("đúng", "supports"),
        ("không đúng", "refutes"),
        ("không chính xác", "refutes"),
        ("thiếu ngữ cảnh", "neutral"),
        ("gây hiểu lầm", "refutes"),
        ("đúng một phần", "neutral"),
        ("phần lớn đúng", "supports"),
        ("phần lớn sai", "refutes"),
        ("  NOT   TRUE! ", "refutes"),
        ("ĐÚNG", "supports"),
        ("đu\u0301ng", "supports"),
        ("unknown", "neutral"),
        ("", "neutral"),
        ("not necessarily true", "neutral"),
    ],
)
def test_rating_stance(service, rating, expected):
    assert service._determine_stance(rating) == expected


@pytest.fixture
def service():
    client = httpx.AsyncClient()
    svc = FactCheckService(client=client)
    yield svc
    # we could close client, but in tests it's okay


@pytest.mark.asyncio
@respx.mock
async def test_factcheck_has_results(service: FactCheckService, monkeypatch):
    monkeypatch.setattr(settings, "factcheck_api_key", "test_key")

    respx.get("https://factchecktools.googleapis.com/v1alpha1/claims:search").mock(
        return_value=httpx.Response(
            200,
            json={
                "claims": [
                    {
                        "text": "The earth is flat",
                        "claimReview": [
                            {
                                "publisher": {"name": "PolitiFact"},
                                "url": "https://example.com/flat-earth",
                                "title": "No, the earth is not flat",
                                "textualRating": "Pants on Fire",
                            }
                        ],
                    }
                ]
            },
        )
    )

    ctx = AnalysisContext(text="The earth is flat", lang="en")
    result = await service.check(ctx)

    assert result.status == "ok"
    assert len(result.sources) == 1
    assert result.sources[0].title == "No, the earth is not flat"
    assert result.sources[0].publisher == "PolitiFact"
    assert result.sources[0].stance == "refutes"
    assert result.sources[0].original_stance == "refutes"
    assert result.sources[0].claim_text == "The earth is flat"


@pytest.mark.asyncio
@respx.mock
async def test_factcheck_empty_then_retry(service: FactCheckService, monkeypatch):
    monkeypatch.setattr(settings, "factcheck_api_key", "test_key")

    # First call with languageCode returns empty
    route1 = respx.get(
        "https://factchecktools.googleapis.com/v1alpha1/claims:search",
        params={
            "key": "test_key",
            "query": "Some query",
            "pageSize": "10",
            "languageCode": "en",
        },
    ).mock(return_value=httpx.Response(200, json={}))

    # Second call without languageCode returns a result
    route2 = respx.get(
        "https://factchecktools.googleapis.com/v1alpha1/claims:search",
        params={"key": "test_key", "query": "Some query", "pageSize": "10"},
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "claims": [
                    {
                        "text": "Some query",
                        "claimReview": [
                            {
                                "publisher": {"name": "Snopes"},
                                "url": "https://example.com/some-query",
                                "textualRating": "Mostly True",
                            }
                        ],
                    }
                ]
            },
        )
    )

    ctx = AnalysisContext(text="Some query", lang="en", search_queries=["Some query"])
    result = await service.check(ctx)

    assert route1.called
    assert route2.called
    assert result.status == "ok"
    assert len(result.sources) == 1
    assert result.sources[0].stance == "supports"


@pytest.mark.asyncio
@respx.mock
async def test_factcheck_empty_all(service: FactCheckService, monkeypatch):
    monkeypatch.setattr(settings, "factcheck_api_key", "test_key")

    respx.get("https://factchecktools.googleapis.com/v1alpha1/claims:search").mock(
        return_value=httpx.Response(200, json={})
    )

    ctx = AnalysisContext(text="No one ever said this", lang="vi")
    result = await service.check(ctx)

    assert result.status == "empty"


@pytest.mark.asyncio
@respx.mock
async def test_factcheck_4xx(service: FactCheckService, monkeypatch):
    monkeypatch.setattr(settings, "factcheck_api_key", "SECRET_KEY_123")

    respx.get("https://factchecktools.googleapis.com/v1alpha1/claims:search").mock(
        return_value=httpx.Response(403, json={"error": "Invalid API key"})
    )

    ctx = AnalysisContext(text="test")
    result = await service.check(ctx)

    assert result.status == "error"
    # Ensure key is not leaked
    assert "SECRET_KEY_123" not in result.error
    assert "***" in result.error


@pytest.mark.asyncio
@respx.mock
async def test_factcheck_5xx(service: FactCheckService, monkeypatch):
    monkeypatch.setattr(settings, "factcheck_api_key", "test_key")

    respx.get("https://factchecktools.googleapis.com/v1alpha1/claims:search").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    ctx = AnalysisContext(text="test")
    result = await service.check(ctx)

    assert result.status == "error"
    assert "500" in result.error


@pytest.mark.asyncio
@respx.mock
async def test_factcheck_timeout(service: FactCheckService, monkeypatch):
    monkeypatch.setattr(settings, "factcheck_api_key", "test_key")

    respx.get("https://factchecktools.googleapis.com/v1alpha1/claims:search").mock(
        side_effect=httpx.TimeoutException("Timeout")
    )

    ctx = AnalysisContext(text="test")
    result = await service.check(ctx)

    assert result.status == "error"
    assert "Timeout" in result.error
