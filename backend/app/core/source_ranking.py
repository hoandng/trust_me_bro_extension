import json
from pathlib import Path
from urllib.parse import urlsplit

from app.schemas.response import Source

TIER_ORDER = ("tier1", "tier2", "default")
with Path(__file__).with_name("trusted_domains.json").open(encoding="utf-8") as config:
    data = json.load(config)
    TRUSTED_DOMAINS = {
        tier: tuple(domain.lower().rstrip(".") for domain in data[tier])
        for tier in TIER_ORDER
    }
    SOURCE_DISPLAY_NAMES = {
        domain.lower().rstrip("."): name
        for domain, name in data.get("display_names", {}).items()
    }


def _web_host(url: str) -> str:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return ""
    if parsed.scheme in ("http", "https"):
        return (parsed.hostname or "").rstrip(".")
    return ""


def _matches_domain(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def source_tier(url: str) -> str:
    host = _web_host(url)
    for tier in TIER_ORDER:
        if any(_matches_domain(host, domain) for domain in TRUSTED_DOMAINS[tier]):
            return tier
    return "default"


def source_display_name(url: str) -> str | None:
    host = _web_host(url)
    domain = max(
        (name for name in SOURCE_DISPLAY_NAMES if _matches_domain(host, name)),
        key=len,
        default=None,
    )
    return SOURCE_DISPLAY_NAMES.get(domain) if domain is not None else None


def rank_sources(sources: list[Source]) -> list[Source]:
    return sorted(sources, key=lambda source: TIER_ORDER.index(source_tier(source.url)))
