"""API endpoints for text analysis."""

# FastAPI is provided by the backend environment; keep editor diagnostics from
# treating the application dependency as a missing local module.
# pyright: reportMissingImports=false
import logging

from fastapi import APIRouter, Depends

from app.schemas.request import AnalyzeRequest
from app.schemas.response import AnalyzeResponse, ServiceStatus, Source
from app.api.deps import verify_api_key, get_orchestrator
from app.orchestrator.analysis_orchestrator import AnalysisOrchestrator
from app.schemas.internal import AnalysisContext

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(
    request: AnalyzeRequest, 
    api_key: str = Depends(verify_api_key),
    orchestrator: AnalysisOrchestrator = Depends(get_orchestrator)
):
    # Do not log user text content directly according to requirements
    logger.info(f"Received analysis request for platform {request.platform} with text length {len(request.text)}")
    
    ctx = AnalysisContext(
        text=request.text,
        lang=request.lang
    )

    return await orchestrator.analyze(ctx)
