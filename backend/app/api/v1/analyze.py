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
    enforce_daily_key_limit,
    enforce_global_daily_limit,
    get_analysis_cache,
    get_metrics_store,
    get_orchestrator,
    verify_ip_limit,
)
from app.core.analysis_cache import AnalysisCache, CacheKey
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
    api_key: Annotated[str, Depends(verify_ip_limit)],
    orchestrator: Annotated[AnalysisOrchestrator, Depends(get_orchestrator)],
    store: Annotated[MetricsStore, Depends(get_metrics_store)],
    cache: Annotated[AnalysisCache, Depends(get_analysis_cache)],
):
    # Do not log user text content directly according to requirements
    logger.info(
        f"Received analysis request for platform {request.platform} with text length {len(request.text)}"
    )

    started = monotonic()
    model_id = request.model_id or settings.gemini_model
    cache_key = None
    result = None
    if not request.bypass_cache:
        cache_key = CacheKey.for_request(request.text, model_id, request.lang)
        try:
            result = await run_in_threadpool(cache.get, cache_key)
        except sqlite3.Error:
            logger.warning("Unable to read analysis cache")

    if result is None:
        enforce_daily_key_limit(api_key)
    enforce_global_daily_limit()

    request_id = uuid4()
    created_at = datetime.now(UTC).isoformat()
    digest = content_digest(request.text)
    metrics = AnalysisMetrics(requested_model=model_id, cache_hit=result is not None)
    token = current_metrics.set(metrics)
    status_code = 500
    try:
        if result is None:
            ctx = AnalysisContext(text=request.text, lang=request.lang)
            result = await orchestrator.analyze(ctx, model_id=request.model_id)
        result.request_id = request_id
        status_code = 200
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

    if cache_key is not None and not metrics.cache_hit:
        try:
            await run_in_threadpool(
                cache.save,
                cache_key,
                result,
                text=request.text,
                page_url=request.page_url,
                timed_out=metrics.timed_out,
            )
        except sqlite3.Error:
            logger.warning("Unable to write analysis cache")
    return result


@router.get("/models")
async def list_models(api_key: str = Depends(authenticate_api_key)):
    return {
        "default_model": settings.gemini_model,
        "models": settings.available_gemini_models,
    }
