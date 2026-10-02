import pytest
import respx
import httpx
from app.services.tavily_service import TavilySearchService
from app.schemas.internal import AnalysisContext
from app.core.config import settings

@pytest.fixture
def service():
    client = httpx.AsyncClient()
    svc = TavilySearchService(client=client)
    yield svc

@pytest.mark.asyncio
@respx.mock
async def test_tavily_has_results(service: TavilySearchService, monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", "test_key")
    
    respx.post("https://api.tavily.com/search").mock(
        return_value=httpx.Response(200, json={
            "query": "Who won the World Cup 2022?",
            "results": [
                {
                    "title": "2022 FIFA World Cup",
                    "url": "https://en.wikipedia.org/wiki/2022_FIFA_World_Cup",
                    "content": "Argentina won the 2022 FIFA World Cup.",
                    "score": 0.99,
                    "raw_content": None
                }
            ]
        })
    )
    
    ctx = AnalysisContext(text="Who won the World Cup 2022?")
    result = await service.check(ctx)
    
    assert result.status == "ok"
    assert len(result.sources) == 1
    assert result.sources[0].title == "2022 FIFA World Cup"
    assert result.sources[0].publisher == "en.wikipedia.org"
    assert result.sources[0].snippet == "Argentina won the 2022 FIFA World Cup."
    assert result.sources[0].stance == "neutral"

@pytest.mark.asyncio
@respx.mock
async def test_tavily_empty_results(service: TavilySearchService, monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", "test_key")
    
    respx.post("https://api.tavily.com/search").mock(
        return_value=httpx.Response(200, json={
            "query": "Gibberish 123456789",
            "results": []
        })
    )
    
    ctx = AnalysisContext(text="Gibberish 123456789")
    result = await service.check(ctx)
    
    assert result.status == "empty"
    assert len(result.sources) == 0

@pytest.mark.asyncio
@respx.mock
async def test_tavily_4xx(service: TavilySearchService, monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", "SECRET_KEY_123")
    
    respx.post("https://api.tavily.com/search").mock(
        return_value=httpx.Response(401, json={"error": "Invalid API key"})
    )
    
    ctx = AnalysisContext(text="test")
    result = await service.check(ctx)
    
    assert result.status == "error"
    # Ensure key is not leaked
    assert "SECRET_KEY_123" not in result.error

@pytest.mark.asyncio
@respx.mock
async def test_tavily_5xx(service: TavilySearchService, monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", "test_key")
    
    respx.post("https://api.tavily.com/search").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    
    ctx = AnalysisContext(text="test")
    result = await service.check(ctx)
    
    assert result.status == "error"
    assert "500" in result.error

@pytest.mark.asyncio
@respx.mock
async def test_tavily_timeout(service: TavilySearchService, monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", "test_key")
    
    respx.post("https://api.tavily.com/search").mock(
        side_effect=httpx.TimeoutException("Timeout")
    )
    
    ctx = AnalysisContext(text="test")
    result = await service.check(ctx)
    
    assert result.status == "error"
    assert "Timeout" in result.error

@pytest.mark.asyncio
@respx.mock
async def test_tavily_truncates_snippet(service: TavilySearchService, monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", "test_key")
    
    long_content = "A" * 400
    expected_snippet = ("A" * 300) + "..."
    
    respx.post("https://api.tavily.com/search").mock(
        return_value=httpx.Response(200, json={
            "query": "long text",
            "results": [
                {
                    "title": "Long text article",
                    "url": "https://example.com/long",
                    "content": long_content
                }
            ]
        })
    )
    
    ctx = AnalysisContext(text="long text")
    result = await service.check(ctx)
    
    assert result.status == "ok"
    assert result.sources[0].snippet == expected_snippet
    assert len(result.sources[0].snippet) == 303
