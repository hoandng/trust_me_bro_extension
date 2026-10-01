import asyncio
import pytest
from app.schemas.internal import AnalysisContext, ServiceResult
from app.services.base_service import BaseService, safe_execute
from app.orchestrator.analysis_orchestrator import AnalysisOrchestrator

class FakeFactCheckService(BaseService):
    @property
    def name(self) -> str:
        return "factcheck"

    @safe_execute(timeout_seconds=0.1)
    async def check(self, ctx: AnalysisContext) -> ServiceResult:
        return ServiceResult(
            service=self.name,
            status="ok",
            sources=[]
        )

class FakeTavilyTimeoutService(BaseService):
    @property
    def name(self) -> str:
        return "tavily"

    @safe_execute(timeout_seconds=0.1)
    async def check(self, ctx: AnalysisContext) -> ServiceResult:
        await asyncio.sleep(0.5) # Should trigger timeout
        return ServiceResult(
            service=self.name,
            status="ok",
            sources=[]
        )

class FakeGeminiErrorService(BaseService):
    @property
    def name(self) -> str:
        return "gemini"
        
    @safe_execute(timeout_seconds=0.1)
    async def check(self, ctx: AnalysisContext) -> ServiceResult:
        raise ValueError("Simulated Exception")

@pytest.mark.asyncio
async def test_orchestrator_degraded_performance():
    ctx = AnalysisContext(text="This is a test claim.")
    
    # 1 ok, 1 timeout, 1 error
    services = [
        FakeFactCheckService(),
        FakeTavilyTimeoutService(),
        FakeGeminiErrorService()
    ]
    
    orchestrator = AnalysisOrchestrator(services)
    response = await orchestrator.analyze(ctx)
    
    # Check that response is returned and not crashed
    assert response is not None
    
    # Check statuses
    assert response.service_status.factcheck == "ok"
    assert response.service_status.tavily == "error" # due to timeout
    assert response.service_status.gemini == "error" # due to exception
    
    # degraded functionality still handles successful parts
    assert response.verdict == "likely_true"
