"""Authentication dependencies for API routes."""

# FastAPI is provided by the backend environment; keep editor diagnostics from
# treating the application dependency as a missing local module.
# pyright: reportMissingImports=false
import secrets
from ipaddress import IPv4Address, IPv6Address, ip_address

from app.core.config import settings
from app.core.metrics import MetricsStore
from app.orchestrator.analysis_orchestrator import AnalysisOrchestrator
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
admin_key_header = APIKeyHeader(name="X-Admin-API-Key", auto_error=False)


def authenticate_api_key(api_key: str = Security(api_key_header)) -> str:
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

    return api_key


def _canonical_ip(value: str) -> IPv4Address | IPv6Address:
    if "%" in value:
        raise ValueError("IP scope identifiers are not accepted")
    address = ip_address(value)
    if isinstance(address, IPv6Address) and address.ipv4_mapped:
        return address.ipv4_mapped
    return address


def _is_trusted_proxy(address: IPv4Address | IPv6Address) -> bool:
    return any(address in network for network in settings.trusted_proxy_networks)


def _rate_limit_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    try:
        peer_address = _canonical_ip(peer)
    except ValueError:
        return peer
    if not settings.trust_proxy_headers or not _is_trusted_proxy(peer_address):
        return str(peer_address)

    # Mỗi proxy tin cậy thêm IP mà nó quan sát vào cuối chuỗi.
    forwarded = request.headers.getlist("x-forwarded-for")
    for header in reversed(forwarded):
        for hop in reversed(header.split(",")):
            try:
                address = _canonical_ip(hop.strip())
            except ValueError:
                return str(peer_address)
            if not _is_trusted_proxy(address):
                return str(address)
    return str(peer_address)


def verify_api_key(
    request: Request, api_key: str = Depends(authenticate_api_key)
) -> str:
    from app.core.rate_limit import limiter

    # Rate limit by IP
    client_ip = _rate_limit_ip(request)
    ip_retry = limiter.check_ip_limit(client_ip, settings.rate_limit_per_minute_ip, 60)
    if ip_retry > 0:
        raise HTTPException(
            status_code=429,
            detail="Too Many Requests",
            headers={"Retry-After": str(ip_retry)},
        )

    # Rate limit by Key
    key_retry = limiter.check_key_limit(api_key, settings.rate_limit_per_day_key, 86400)
    if key_retry > 0:
        raise HTTPException(
            status_code=429,
            detail="Too Many Requests (Key Quota Exceeded)",
            headers={"Retry-After": str(key_retry)},
        )

    # Global daily limit check (kill switch)
    if not limiter.check_global_daily_limit(settings.daily_analyze_limit_global):
        raise HTTPException(
            status_code=429,
            detail="Global Daily Limit Exceeded",
            headers={"Retry-After": "86400"},
        )

    return api_key


def get_orchestrator(request: Request) -> AnalysisOrchestrator:
    return request.app.state.orchestrator


def get_metrics_store(request: Request) -> MetricsStore:
    return request.app.state.metrics_store


def authenticate_admin(api_key: str | None = Security(admin_key_header)) -> None:
    key = settings.admin_api_key
    if not key or key == settings.extension_api_key:
        raise HTTPException(status_code=503, detail="Admin API is not configured")
    if not api_key or not secrets.compare_digest(api_key.encode(), key.encode()):
        raise HTTPException(status_code=401, detail="Invalid admin API key")
