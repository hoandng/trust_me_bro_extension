from unittest.mock import AsyncMock

import pytest
from app.orchestrator.analysis_orchestrator import AnalysisOrchestrator
from app.schemas.internal import AnalysisContext, ServiceResult
from app.schemas.response import Source
from app.services.gemini_service import Assessment, ClaimExtraction


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
