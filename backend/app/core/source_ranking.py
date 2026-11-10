import json
from pathlib import Path
from urllib.parse import urlsplit

from app.schemas.response import Source

TIER_ORDER = ("tier1", "tier2", "default")
with Path(__file__).with_name("trusted_domains.json").open(encoding="utf-8") as config:
    TRUSTED_DOMAINS = {
        tier: tuple(domain.lower().rstrip(".") for domain in domains)
        for tier, domains in json.load(config).items()
    }


def source_tier(url: str) -> str:
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").rstrip(".")
    except ValueError:
        return "default"
    if parsed.scheme in ("http", "https") and host:
        for tier in TIER_ORDER:
            if any(
                host == domain or host.endswith("." + domain)
                for domain in TRUSTED_DOMAINS[tier]
            ):
                return tier
    return "default"


def rank_sources(sources: list[Source]) -> list[Source]:
    return sorted(sources, key=lambda source: TIER_ORDER.index(source_tier(source.url)))
