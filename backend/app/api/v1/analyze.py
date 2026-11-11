"""API endpoints for text analysis."""

# FastAPI is provided by the backend environment; keep editor diagnostics from
# treating the application dependency as a missing local module.
# pyright: reportMissingImports=false
import asyncio
import logging
import sqlite3
from datetime import UTC, datetime
from time import monotonic
from typing import Annotated
from uuid import uuid4

from app.api.deps import (
    authenticate_api_key,
    get_metrics_store,
    get_orchestrator,
    verify_api_key,
)
from app.core.config import settings
from app.core.metrics import (
    AnalysisMetrics,
    MetricsStore,
    content_digest,
    current_metrics,
)
from app.orchestrator.analysis_orchestrator import AnalysisOrchestrator
from app.schemas.internal import AnalysisContext
from app.schemas.request import AnalyzeRequest
from app.schemas.response import AnalyzeResponse
from app.services.gemini_model_pool import GeminiQuotaExhausted
from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(
    request: AnalyzeRequest,
    api_key: Annotated[str, Depends(verify_api_key)],
    orchestrator: Annotated[AnalysisOrchestrator, Depends(get_orchestrator)],
    store: Annotated[MetricsStore, Depends(get_metrics_store)],
):
    # Do not log user text content directly according to requirements
    logger.info(
        f"Received analysis request for platform {request.platform} with text length {len(request.text)}"
    )

    request_id = uuid4()
    created_at = datetime.now(UTC).isoformat()
    digest = content_digest(request.text)
    metrics = AnalysisMetrics(requested_model=request.model_id or settings.gemini_model)
    started = monotonic()
    token = current_metrics.set(metrics)
    result = None
    status_code = 500
    try:
        ctx = AnalysisContext(text=request.text, lang=request.lang)
        result = await orchestrator.analyze(ctx, model_id=request.model_id)
        result.request_id = request_id
        status_code = 200
        return result
    except GeminiQuotaExhausted as error:
        status_code = 503
        raise HTTPException(
            status_code=503,
            detail=str(error),
            headers={"Retry-After": str(error.retry_after)},
        ) from error
    except asyncio.CancelledError:
        status_code = 499
        raise
    finally:
        current_metrics.reset(token)
        total_ms = metrics.total_ms
        if total_ms is None:
            total_ms = round((monotonic() - started) * 1000)
        try:
            await run_in_threadpool(
                store.record,
                request_id=str(request_id),
                created_at=created_at,
                platform=request.platform,
                text_length=len(request.text),
                content_hash=digest,
                http_status=status_code,
                verdict=result.verdict if result is not None else None,
                confidence=result.confidence_score if result is not None else None,
                total_ms=total_ms,
                metrics=metrics,
            )
        except sqlite3.Error:
            logger.error("Unable to persist analysis metrics")
            if status_code == 200:
                raise HTTPException(
                    status_code=503, detail="Metrics storage unavailable"
                ) from None


@router.get("/models")
async def list_models(api_key: str = Depends(authenticate_api_key)):
    return {
        "default_model": settings.gemini_model,
        "models": settings.available_gemini_models,
    }
