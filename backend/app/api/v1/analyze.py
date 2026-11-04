"""API endpoints for text analysis."""

# FastAPI is provided by the backend environment; keep editor diagnostics from
# treating the application dependency as a missing local module.
# pyright: reportMissingImports=false
import logging

from fastapi import APIRouter, Depends, HTTPException
from app.core.config import settings
from app.services.gemini_model_pool import GeminiQuotaExhausted

from app.schemas.request import AnalyzeRequest
from app.schemas.response import AnalyzeResponse, ServiceStatus, Source
from app.api.deps import verify_api_key, authenticate_api_key, get_orchestrator
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

    service = getattr(orchestrator, "gemini_service", None)
    if service is not None:
        service.select_model(request.model_id)
    try:
        response = await orchestrator.analyze(ctx)
    except GeminiQuotaExhausted as error:
        raise HTTPException(status_code=503, detail=str(error),
                            headers={"Retry-After": str(error.retry_after)}) from error
    if service is not None:
        response.model_usage = service.model_usage
    return response


@router.get("/models")
async def list_models(api_key: str = Depends(authenticate_api_key)):
    return {"default_model": settings.gemini_model, "models": settings.available_gemini_models}
