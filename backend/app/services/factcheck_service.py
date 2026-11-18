import re
import unicodedata
from typing import Any

import httpx

from app.core.config import settings
from app.core.metrics import current_metrics
from app.schemas.internal import AnalysisContext, ServiceResult
from app.schemas.response import Source
from app.services.base_service import BaseService, safe_execute

# Tra cứu toàn nhãn để không nhầm phủ định hoặc mức độ với từ "true".
RATING_GROUPS = {
    "supports": (
        "true",
        "accurate",
        "correct",
        "mostly true",
        "mostly accurate",
        "đúng",
        "đúng sự thật",
        "chính xác",
        "phần lớn đúng",
        "hầu hết đúng",
    ),
    "refutes": (
        "false",
        "fake",
        "pants on fire",
        "misleading",
        "incorrect",
        "untrue",
        "hoax",
        "not true",
        "not accurate",
        "not correct",
        "mostly false",
        "mostly inaccurate",
        "sai",
        "sai sự thật",
        "không đúng",
        "không chính xác",
        "tin giả",
        "giả mạo",
        "gây hiểu lầm",
        "phần lớn sai",
        "hầu hết sai",
    ),
    "neutral": (
        "partly true",
        "partially true",
        "half true",
        "partly false",
        "half false",
        "partially false",
        "partly accurate",
        "mixed",
        "missing context",
        "out of context",
        "unverified",
        "unproven",
        "đúng một phần",
        "sai một phần",
        "nửa đúng nửa sai",
        "thiếu ngữ cảnh",
        "ngoài ngữ cảnh",
        "chưa kiểm chứng",
    ),
}
RATING_LOOKUP = {
    rating: stance for stance, ratings in RATING_GROUPS.items() for rating in ratings
}


class FactCheckService(BaseService):
    def __init__(self, client: httpx.AsyncClient | None = None):
        # Allow passing an existing client for lifespan reuse
        self._owns_client = client is None
        self._client = client if client is not None else httpx.AsyncClient(timeout=10.0)

    @property
    def name(self) -> str:
        return "factcheck"

    async def aclose(self):
        if self._owns_client:
            await self._client.aclose()

    def _determine_stance(self, rating: str) -> str:
        normalized = unicodedata.normalize("NFC", rating or "").casefold()
        normalized = re.sub(r"[-‐‑–—]", " ", normalized)
        normalized = " ".join(normalized.split()).strip(" .!?:;")
        return RATING_LOOKUP.get(normalized, "neutral")

    def _parse_claims(self, claims: list[dict[str, Any]]) -> list[Source]:
        sources = []
        for claim in claims:
            # We look at claimReview array
            reviews = claim.get("claimReview", [])
            for review in reviews:
                publisher_info = review.get("publisher", {})
                publisher_name = publisher_info.get("name", "Unknown")

                url = review.get("url", "")
                title = review.get("title", claim.get("text", ""))
                rating = review.get("textualRating", "")

                if url:
                    stance = self._determine_stance(rating)
                    sources.append(
                        Source(
                            title=title,
                            url=url,
                            publisher=publisher_name,
                            snippet=rating,
                            stance=stance,
                            original_stance=stance,
                            claim_text=claim.get("text"),
                        )
                    )
        return sources

    @safe_execute(timeout_seconds=10.0)
    async def check(self, ctx: AnalysisContext) -> ServiceResult:
        query = ""
        if ctx.search_queries and len(ctx.search_queries) > 0:
            query = ctx.search_queries[0]
        elif ctx.claim:
            query = ctx.claim
        else:
            query = ctx.text[:500]

        if not query.strip():
            return ServiceResult(service=self.name, status="empty", sources=[])

        api_key = settings.factcheck_api_key
        if not api_key:
            return ServiceResult(
                service=self.name,
                status="error",
                error="FactCheck API key not configured",
            )

        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

        # Try with language first if provided
        params = {"key": api_key, "query": query, "pageSize": 10}

        if ctx.lang:
            params["languageCode"] = ctx.lang

        try:
            metrics = current_metrics.get()
            if metrics is not None:
                metrics.factcheck_calls += 1
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            claims = data.get("claims", [])

            # If empty and we used language code, retry without language code
            if not claims and ctx.lang:
                params.pop("languageCode", None)
                if metrics is not None:
                    metrics.factcheck_calls += 1
                response = await self._client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                claims = data.get("claims", [])

            if not claims:
                return ServiceResult(service=self.name, status="empty", sources=[])

            sources = self._parse_claims(claims)

            if not sources:
                return ServiceResult(service=self.name, status="empty", sources=[])

            return ServiceResult(service=self.name, status="ok", sources=sources)

        except httpx.HTTPStatusError as e:
            # Mask API key in error message
            error_msg = str(e).replace(api_key, "***")
            return ServiceResult(
                service=self.name,
                status="error",
                error=f"HTTP Error: {e.response.status_code} - {error_msg}",
            )
        except Exception as e:  # noqa: BLE001 - Service boundary returns degraded results.
            error_msg = str(e).replace(api_key, "***")
            return ServiceResult(
                service=self.name, status="error", error=f"Request failed: {error_msg}"
            )
