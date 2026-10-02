"""Authentication dependencies for API routes."""

# FastAPI is provided by the backend environment; keep editor diagnostics from
# treating the application dependency as a missing local module.
# pyright: reportMissingImports=false
import secrets
from fastapi import Depends, HTTPException, Security, status, Request
from fastapi.security import APIKeyHeader

from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(request: Request, api_key: str = Security(api_key_header)) -> str:
    from app.core.rate_limit import limiter

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
        )
    
    if not settings.extension_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server API key not configured",
        )
        
    if not secrets.compare_digest(api_key, settings.extension_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
        
    # Rate limit by IP
    client_ip = request.client.host if request.client else "unknown"
    ip_retry = limiter.check_ip_limit(client_ip, settings.rate_limit_per_minute_ip, 60)
    if ip_retry > 0:
        raise HTTPException(
            status_code=429,
            detail="Too Many Requests",
            headers={"Retry-After": str(ip_retry)}
        )
        
    # Rate limit by Key
    key_retry = limiter.check_key_limit(api_key, settings.rate_limit_per_day_key, 86400)
    if key_retry > 0:
        raise HTTPException(
            status_code=429,
            detail="Too Many Requests (Key Quota Exceeded)",
            headers={"Retry-After": str(key_retry)}
        )
        
    # Global daily limit check (kill switch)
    if not limiter.check_global_daily_limit(settings.daily_analyze_limit_global):
        raise HTTPException(
            status_code=429,
            detail="Global Daily Limit Exceeded",
            headers={"Retry-After": "86400"}
        )
        
    return api_key

from app.services.gemini_service import GeminiService
from app.services.factcheck_service import FactCheckService
from app.services.tavily_service import TavilySearchService
from app.orchestrator.analysis_orchestrator import AnalysisOrchestrator

def get_orchestrator() -> AnalysisOrchestrator:
    return AnalysisOrchestrator(
        gemini_service=GeminiService(),
        factcheck_service=FactCheckService(),
        tavily_service=TavilySearchService()
    )
