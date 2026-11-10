from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.schemas.internal import AnalysisContext, ServiceResult
from app.schemas.response import Source
from app.services.base_service import BaseService, safe_execute


class TavilySearchService(BaseService):
    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client or httpx.AsyncClient(timeout=10.0)

    @property
    def name(self) -> str:
        return "tavily"

    async def aclose(self):
        if self._client:
            await self._client.aclose()

    def _extract_domain(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            return parsed.netloc.removeprefix("www.")
        except ValueError:
            return "Unknown"

    def _parse_results(self, results: list[dict[str, Any]]) -> list[Source]:
        sources = []
        for result in results:
            url = result.get("url", "")
            title = result.get("title", "")
            content = result.get("content", "")
            published_date = result.get("published_date")

            # Truncate content to <= 300 characters
            snippet = content[:300] + ("..." if len(content) > 300 else "")

            if url:
                sources.append(
                    Source(
                        title=title,
                        url=url,
                        publisher=self._extract_domain(url),
                        snippet=snippet,
                        stance="neutral",
                        published_date=published_date
                        if isinstance(published_date, str)
                        else None,
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

        api_key = settings.tavily_api_key
        if not api_key:
            return ServiceResult(
                service=self.name, status="error", error="Tavily API key not configured"
            )

        url = "https://api.tavily.com/search"

        payload = {
            "query": query,
            "search_depth": "basic",
            "auto_parameters": False,
            "include_published_date": True,
            "include_answer": False,
            "max_results": 5,
        }

        if settings.tavily_include_domains:
            payload["include_domains"] = settings.tavily_include_domains

        if settings.tavily_exclude_domains:
            payload["exclude_domains"] = settings.tavily_exclude_domains

        try:
            for topic in ("news", "general"):
                response = await self._client.post(
                    url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={**payload, "topic": topic},
                )
                response.raise_for_status()
                sources = self._parse_results(response.json().get("results") or [])
                if sources:
                    return ServiceResult(
                        service=self.name, status="ok", sources=sources
                    )
            return ServiceResult(service=self.name, status="empty", sources=[])

        except httpx.HTTPStatusError as e:
            return ServiceResult(
                service=self.name,
                status="error",
                error=f"HTTP Error: {e.response.status_code}",
            )
        except Exception as e:  # noqa: BLE001 - Không đưa dữ liệu request vào thông báo lỗi.
            return ServiceResult(
                service=self.name,
                status="error",
                error=f"Request failed: {type(e).__name__}",
            )
