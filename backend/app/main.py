from contextlib import AsyncExitStack, asynccontextmanager

import httpx
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import analyze
from app.core.config import settings
from app.core.logging import setup_logging
from app.orchestrator.analysis_orchestrator import AnalysisOrchestrator
from app.services.factcheck_service import FactCheckService
from app.services.gemini_service import GeminiService
from app.services.tavily_service import TavilySearchService

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        client = await stack.enter_async_context(httpx.AsyncClient(timeout=10.0))
        gemini = GeminiService()
        stack.push_async_callback(gemini.aclose)
        app.state.http_client = client
        app.state.orchestrator = AnalysisOrchestrator(
            gemini, FactCheckService(client), TavilySearchService(client)
        )
        try:
            yield
        finally:
            del app.state.orchestrator
            del app.state.http_client


app_kwargs = {"title": "FactCheck API", "version": "1.0.0"}
if settings.env == "production":
    app_kwargs["docs_url"] = None
    app_kwargs["redoc_url"] = None
    app_kwargs["openapi_url"] = None

app = FastAPI(lifespan=lifespan, **app_kwargs)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # Check body size
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.max_body_size_bytes:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": "Request body too large"},
        )

    response = await call_next(request)

    # Add Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )

    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging

    logger = logging.getLogger(__name__)
    logger.error(
        "Internal Server Error", exc_info=False
    )  # Do not log stacktrace with request payload directly
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


if settings.allowed_origins:
    origins = [
        origin.strip()
        for origin in settings.allowed_origins.split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(analyze.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
