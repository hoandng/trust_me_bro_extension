"""API endpoints for text analysis."""

# FastAPI is provided by the backend environment; keep editor diagnostics from
# treating the application dependency as a missing local module.
# pyright: reportMissingImports=false
import logging
from typing import Annotated

from app.api.deps import authenticate_api_key, get_orchestrator, verify_api_key
from app.core.config import settings
from app.orchestrator.analysis_orchestrator import AnalysisOrchestrator
from app.schemas.internal import AnalysisContext
from app.schemas.request import AnalyzeRequest
from app.schemas.response import AnalyzeResponse
from app.services.gemini_model_pool import GeminiQuotaExhausted
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(
    request: AnalyzeRequest,
    api_key: Annotated[str, Depends(verify_api_key)],
    orchestrator: Annotated[AnalysisOrchestrator, Depends(get_orchestrator)],
):
    # Do not log user text content directly according to requirements
    logger.info(
        f"Received analysis request for platform {request.platform} with text length {len(request.text)}"
    )

    ctx = AnalysisContext(text=request.text, lang=request.lang)

    try:
        return await orchestrator.analyze(ctx, model_id=request.model_id)
    except GeminiQuotaExhausted as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
            headers={"Retry-After": str(error.retry_after)},
        ) from error


@router.get("/models")
async def list_models(api_key: str = Depends(authenticate_api_key)):
    return {
        "default_model": settings.gemini_model,
        "models": settings.available_gemini_models,
    }
