import asyncio
import json
from unittest.mock import AsyncMock

import httpx
import pytest
import respx
from app.core.config import settings
from app.orchestrator.analysis_orchestrator import AnalysisOrchestrator
from app.schemas.internal import AnalysisContext, ServiceResult
from app.schemas.response import Source
from app.services.factcheck_service import FactCheckService
from app.services.gemini_service import Assessment, ClaimExtraction
from app.services.tavily_service import TavilySearchService


def gemini_with_queries(queries):
    gemini = MockGeminiService()
    gemini.extract_claims = AsyncMock(
        return_value=ClaimExtraction(
            main_claim="Synthetic claim",
            search_queries=queries,
            detected_lang="en",
            is_checkable=True,
        )
    )
    return gemini


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("limit", "queries", "expected"),
    [
        (2, ["first", "second", "ignored"], ["first", "second"]),
        (1, ["first", "second"], ["first"]),
        (2, [" first ", "first", "ignored"], ["first"]),
        (2, ["", " "], ["Synthetic claim"]),
    ],
)
@respx.mock
async def test_search_request_budget_includes_fallbacks(
    monkeypatch, limit, queries, expected
):
    monkeypatch.setattr(settings, "search_query_limit", limit)
    monkeypatch.setattr(settings, "factcheck_api_key", "test_key")
    monkeypatch.setattr(settings, "tavily_api_key", "test_key")
    factcheck_route = respx.get(
        "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    ).mock(return_value=httpx.Response(200, json={"claims": []}))
    tavily_route = respx.post("https://api.tavily.com/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )

    async with httpx.AsyncClient() as client:
        result = await AnalysisOrchestrator(
            gemini_with_queries(queries),
            FactCheckService(client),
            TavilySearchService(client),
        ).analyze(AnalysisContext(text="Synthetic post"))

    assert result.verdict == "unverified"
    assert factcheck_route.call_count == tavily_route.call_count == 2 * len(expected)
    assert sorted(
        (
            call.request.url.params["query"],
            call.request.url.params.get("languageCode", ""),
        )
        for call in factcheck_route.calls
    ) == sorted((query, lang) for query in expected for lang in ("en", ""))
    payloads = [json.loads(call.request.content) for call in tavily_route.calls]
    assert sorted(
        (payload["query"], payload["topic"]) for payload in payloads
    ) == sorted((query, topic) for query in expected for topic in ("news", "general"))


@pytest.mark.asyncio
async def test_queries_run_concurrently_and_merge_partial_results(monkeypatch):
    monkeypatch.setattr(settings, "search_query_limit", 2)
    reviewed = Source(
        title="Review",
        url="https://factcheck.org/review",
        original_stance="refutes",
        stance="refutes",
        claim_text="Synthetic claim",
    )
    news = Source(title="Article", url="https://example.com/article")
    other_news = Source(title="Other article", url="https://example.com/other")
    contexts = []
    ready = asyncio.Event()

    async def check(provider, ctx):
        contexts.append(ctx)
        if len(contexts) == 4:
            ready.set()
        await ready.wait()
        query = ctx.search_queries[0]
        if provider == "factcheck":
            if query == "first":
                raise RuntimeError("Synthetic search failure")
            return ServiceResult(service=provider, status="ok", sources=[reviewed])
        return ServiceResult(
            service=provider,
            status="ok",
            sources=[Source(title="Duplicate", url=reviewed.url), news]
            if query == "first"
            else [news, other_news],
        )

    async def check_factcheck(ctx):
        return await check("factcheck", ctx)

    async def check_tavily(ctx):
        return await check("tavily", ctx)

    factcheck = MockFactCheckService()
    tavily = MockTavilyService()
    factcheck.check = AsyncMock(side_effect=check_factcheck)
    tavily.check = AsyncMock(side_effect=check_tavily)

    result = await asyncio.wait_for(
        AnalysisOrchestrator(
            gemini_with_queries(["first", "second"]), factcheck, tavily
        ).analyze(AnalysisContext(text="Synthetic post")),
        timeout=2,
    )

    assert len({id(ctx) for ctx in contexts}) == 4
    assert result.service_status.factcheck == "error"
    assert result.service_status.tavily == "ok"
    assert [source.url for source in result.sources] == [
        reviewed.url,
        news.url,
        other_news.url,
    ]
    assert result.sources[0].original_stance == "refutes"


@pytest.mark.asyncio
async def test_rank_before_limit_and_disallow_override_from_excluded_source():
    factcheck = MockFactCheckService()
    reviewed = Source(
        title="Review",
        url="https://example.com/review",
        original_stance="refutes",
        stance="refutes",
        claim_text="Synthetic claim",
    )
    factcheck.check = AsyncMock(
        return_value=ServiceResult(
            service="factcheck",
            status="ok",
            sources=[reviewed],
        )
    )
    default_sources = [
        Source(title="Article", url=f"https://example.com/{i}") for i in range(8)
    ]
    tier2 = Source(title="Reference", url="https://britannica.com/reference")
    tier1 = Source(title="News", url="https://reuters.com/news")
    # Tám nguồn tier cao hơn sẽ đẩy nguồn Fact Check ra khỏi tập bằng chứng.
    more_tier1 = [
        Source(title="News", url=f"https://reuters.com/{i}") for i in range(6)
    ]
    tavily = MockTavilyService()
    tavily.check = AsyncMock(
        return_value=ServiceResult(
            service="tavily",
            status="ok",
            sources=[*default_sources, tier2, tier1, *more_tier1],
        )
    )
    gemini = gemini_with_queries(["first"])
    gemini.assess = AsyncMock(
        return_value=Assessment(
            verdict="mixed",
            confidence_score=0.4,
            explanation="Synthetic result",
            source_stances=[
                {"url": reviewed.url, "stance": "refutes", "factcheck_match": True}
            ],
        )
    )

    result = await AnalysisOrchestrator(gemini, factcheck, tavily).analyze(
        AnalysisContext(text="Synthetic post")
    )

    assert len(result.sources) == 8
    assert result.sources[0].url == tier1.url
    assert result.sources[-1].url == tier2.url
    assert [source.url for source in gemini.assess.call_args.args[2]] == [
        source.url for source in result.sources
    ]
    assert reviewed.url not in {source.url for source in result.sources}
    assert result.verdict == "mixed"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "original, expected",
    [("refutes", "likely_false"), ("supports", "likely_true"), ("neutral", "mixed")],
)
@pytest.mark.parametrize("match", [True, False, None])
async def test_override_requires_match_and_preserves_factcheck(
    original, expected, match
):
    source = Source(
        title="FactCheck",
        url="https://example.com/fc",
        stance=original,
        original_stance=original,
        claim_text="This is a test claim.",
    )
    fc_result = ServiceResult(service="factcheck", status="ok", sources=[source])
    factcheck = MockFactCheckService()
    factcheck.check = AsyncMock(return_value=fc_result)
    tavily = MockTavilyService()
    tavily_source = Source(title="News", url="https://news.com/1", stance="neutral")
    tavily.check = AsyncMock(
        return_value=ServiceResult(
            service="tavily",
            status="ok",
            sources=[
                Source(title="Duplicate", url=source.url, stance="neutral"),
                tavily_source,
            ],
        )
    )
    entry = {
        "url": source.url,
        "stance": "supports" if original == "refutes" else "refutes",
    }
    if match is not None:
        entry["factcheck_match"] = match
    gemini = MockGeminiService()
    gemini.assess = AsyncMock(
        return_value=Assessment(
            verdict="mixed",
            confidence_score=0.3,
            explanation="Mock",
            source_stances=[entry, {"url": tavily_source.url, "stance": "refutes"}],
        )
    )
    result = await AnalysisOrchestrator(gemini, factcheck, tavily).analyze(
        AnalysisContext(text="Synthetic post")
    )
    assert result.verdict == (expected if match is True else "mixed")
    assert result.confidence_score == (
        0.8 if match is True and original != "neutral" else 0.3
    )
    assert len(result.sources) == 2
    assert result.sources[0].stance == original
    assert result.sources[0].original_stance == original
    assert fc_result.sources[0].stance == original
    assert result.sources[0] is not fc_result.sources[0]
    assert result.sources[1].stance == "refutes"
    assert tavily_source.stance == "neutral"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "claim_text, status", [(None, "ok"), ("  ", "ok"), ("Claim", "error")]
)
async def test_override_rejects_missing_claim_or_failed_assessment(claim_text, status):
    factcheck = MockFactCheckService()
    factcheck.check = AsyncMock(
        return_value=ServiceResult(
            service="factcheck",
            status="ok",
            sources=[
                Source(
                    title="FC",
                    url="https://factcheck.org/1",
                    stance="refutes",
                    original_stance="refutes",
                    claim_text=claim_text,
                )
            ],
        )
    )
    gemini = MockGeminiService()
    gemini.assess = AsyncMock(
        return_value=Assessment(
            verdict="unverified",
            confidence_score=0.1,
            explanation="Mock",
            status=status,
            source_stances=[
                {
                    "url": "https://factcheck.org/1",
                    "stance": "refutes",
                    "factcheck_match": True,
                }
            ],
        )
    )
    result = await AnalysisOrchestrator(gemini, factcheck, MockTavilyService()).analyze(
        AnalysisContext(text="Synthetic post")
    )
    assert result.verdict == "unverified"
    assert result.confidence_score == 0.1


class MockGeminiService:
    def __init__(self, checkable=True, extract_error=False, assess_error=False):
        self.checkable = checkable
        self.extract_error = extract_error
        self.assess_error = assess_error

    async def extract_claims(
        self, text: str, lang: str | None = None
    ) -> ClaimExtraction | None:
        if self.extract_error:
            raise RuntimeError("Mock Extract Error")

        if not self.checkable:
            return ClaimExtraction(
                main_claim="", search_queries=[], detected_lang="vi", is_checkable=False
            )

        return ClaimExtraction(
            main_claim="This is a test claim.",
            search_queries=["test query"],
            detected_lang="vi",
            is_checkable=True,
        )

    async def assess(self, text: str, claim: str, evidence: list) -> Assessment:
        if self.assess_error:
            raise RuntimeError("Mock Assess Error")

        return Assessment(
            verdict="likely_true",
            confidence_score=0.9,
            explanation="Test explanation",
            source_stances=[],
            status="ok",
        )


class MockFactCheckService:
    def __init__(self, status="ok", has_sources=True):
        self.status = status
        self.has_sources = has_sources

    async def check(self, ctx: AnalysisContext) -> ServiceResult:
        if self.status == "error":
            raise RuntimeError("Mock Factcheck Error")

        sources = []
        if self.has_sources:
            sources.append(
                Source(
                    title="FC Title",
                    url="https://factcheck.org/1",
                    publisher="Factcheck",
                    snippet="FC Snippet",
                    stance="supports",
                )
            )

        return ServiceResult(service="factcheck", status=self.status, sources=sources)


class MockTavilyService:
    def __init__(self, status="ok"):
        self.status = status

    async def check(self, ctx: AnalysisContext) -> ServiceResult:
        if self.status == "error":
            raise RuntimeError("Mock Tavily Error")

        return ServiceResult(
            service="tavily",
            status=self.status,
            sources=[
                Source(
                    title="Tavily Title",
                    url="https://news.com/1",
                    publisher="News",
                    snippet="News Snippet",
                    stance="neutral",
                )
            ],
        )


@pytest.mark.asyncio
async def test_orchestrator_all_ok():
    gemini = MockGeminiService()
    factcheck = MockFactCheckService()
    tavily = MockTavilyService()
    orchestrator = AnalysisOrchestrator(gemini, factcheck, tavily)

    ctx = AnalysisContext(text="Test text")
    res = await orchestrator.analyze(ctx)

    assert res.verdict == "likely_true"
    assert res.confidence_score >= 0.8
    assert res.service_status.gemini == "ok"
    assert res.service_status.factcheck == "ok"
    assert res.service_status.tavily == "ok"
    assert len(res.sources) == 2


@pytest.mark.asyncio
async def test_orchestrator_factcheck_empty():
    gemini = MockGeminiService()
    factcheck = MockFactCheckService(status="empty", has_sources=False)
    tavily = MockTavilyService()
    orchestrator = AnalysisOrchestrator(gemini, factcheck, tavily)

    ctx = AnalysisContext(text="Test text")
    res = await orchestrator.analyze(ctx)

    assert res.service_status.factcheck == "empty"
    assert len(res.sources) == 1


@pytest.mark.asyncio
async def test_orchestrator_tavily_error():
    gemini = MockGeminiService()
    factcheck = MockFactCheckService()
    tavily = MockTavilyService(status="error")
    orchestrator = AnalysisOrchestrator(gemini, factcheck, tavily)

    ctx = AnalysisContext(text="Test text")
    res = await orchestrator.analyze(ctx)

    assert res.service_status.tavily == "error"
    assert len(res.sources) == 1


@pytest.mark.asyncio
async def test_orchestrator_not_checkable():
    gemini = MockGeminiService(checkable=False)
    factcheck = MockFactCheckService()
    tavily = MockTavilyService()
    orchestrator = AnalysisOrchestrator(gemini, factcheck, tavily)

    ctx = AnalysisContext(text="Just an opinion")
    res = await orchestrator.analyze(ctx)

    assert res.verdict == "unverified"
    assert res.confidence_score == 0.0


@pytest.mark.asyncio
async def test_orchestrator_gemini_error():
    gemini = MockGeminiService(extract_error=True)
    factcheck = MockFactCheckService()
    tavily = MockTavilyService()
    orchestrator = AnalysisOrchestrator(gemini, factcheck, tavily)

    ctx = AnalysisContext(text="Test")
    res = await orchestrator.analyze(ctx)

    assert res.verdict == "unverified"
    assert res.service_status.gemini == "error"


@pytest.mark.asyncio
async def test_orchestrator_both_empty():
    gemini = MockGeminiService()
    factcheck = MockFactCheckService(status="empty", has_sources=False)
    tavily = MockTavilyService(status="error")  # results in no sources
    orchestrator = AnalysisOrchestrator(gemini, factcheck, tavily)

    ctx = AnalysisContext(text="Test text")
    res = await orchestrator.analyze(ctx)

    assert res.verdict == "unverified"
    assert res.confidence_score <= 0.3
