import asyncio
import pytest
from app.schemas.internal import AnalysisContext, ServiceResult
from app.schemas.response import Source
from app.orchestrator.analysis_orchestrator import AnalysisOrchestrator
from app.services.gemini_service import ClaimExtraction, Assessment

class MockGeminiService:
    def __init__(self, checkable=True, extract_error=False, assess_error=False):
        self.checkable = checkable
        self.extract_error = extract_error
        self.assess_error = assess_error

    async def extract_claims(self, text: str, lang: str | None = None) -> ClaimExtraction | None:
        if self.extract_error:
            raise Exception("Mock Extract Error")
        
        if not self.checkable:
            return ClaimExtraction(
                main_claim="",
                search_queries=[],
                detected_lang="vi",
                is_checkable=False
            )
            
        return ClaimExtraction(
            main_claim="This is a test claim.",
            search_queries=["test query"],
            detected_lang="vi",
            is_checkable=True
        )

    async def assess(self, text: str, claim: str, evidence: list) -> Assessment:
        if self.assess_error:
            raise Exception("Mock Assess Error")
            
        return Assessment(
            verdict="likely_true",
            confidence_score=0.9,
            explanation="Test explanation",
            source_stances=[],
            status="ok"
        )

class MockFactCheckService:
    def __init__(self, status="ok", has_sources=True):
        self.status = status
        self.has_sources = has_sources

    async def check(self, ctx: AnalysisContext) -> ServiceResult:
        if self.status == "error":
            raise Exception("Mock Factcheck Error")
            
        sources = []
        if self.has_sources:
            sources.append(Source(
                title="FC Title",
                url="https://factcheck.org/1",
                publisher="Factcheck",
                snippet="FC Snippet",
                stance="supports"
            ))
            
        return ServiceResult(
            service="factcheck",
            status=self.status,
            sources=sources
        )

class MockTavilyService:
    def __init__(self, status="ok"):
        self.status = status

    async def check(self, ctx: AnalysisContext) -> ServiceResult:
        if self.status == "error":
            raise Exception("Mock Tavily Error")
            
        return ServiceResult(
            service="tavily",
            status=self.status,
            sources=[Source(
                title="Tavily Title",
                url="https://news.com/1",
                publisher="News",
                snippet="News Snippet",
                stance="neutral"
            )]
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
    tavily = MockTavilyService(status="error") # results in no sources
    orchestrator = AnalysisOrchestrator(gemini, factcheck, tavily)
    
    ctx = AnalysisContext(text="Test text")
    res = await orchestrator.analyze(ctx)
    
    assert res.verdict == "unverified"
    assert res.confidence_score <= 0.3
