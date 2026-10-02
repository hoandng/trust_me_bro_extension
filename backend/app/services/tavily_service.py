import httpx
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

from app.schemas.internal import AnalysisContext, ServiceResult
from app.schemas.response import Source
from app.services.base_service import BaseService, safe_execute
from app.core.config import settings

class TavilySearchService(BaseService):
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
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
        except Exception:
            return "Unknown"

    def _parse_results(self, results: List[Dict[str, Any]]) -> List[Source]:
        sources = []
        for result in results:
            url = result.get("url", "")
            title = result.get("title", "")
            content = result.get("content", "")
            
            # Truncate content to <= 300 characters
            snippet = content[:300] + ("..." if len(content) > 300 else "")
            
            if url:
                sources.append(Source(
                    title=title,
                    url=url,
                    publisher=self._extract_domain(url),
                    snippet=snippet,
                    stance="neutral"
                ))
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
             return ServiceResult(
                service=self.name,
                status="empty",
                sources=[]
            )

        api_key = settings.tavily_api_key
        if not api_key:
            return ServiceResult(
                service=self.name,
                status="error",
                error="Tavily API key not configured"
            )

        url = "https://api.tavily.com/search"
        
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "include_answer": False,
            "max_results": 5
        }
        
        if settings.tavily_include_domains:
            payload["include_domains"] = settings.tavily_include_domains
            
        if settings.tavily_exclude_domains:
            payload["exclude_domains"] = settings.tavily_exclude_domains

        try:
            response = await self._client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
                
            if not results:
                return ServiceResult(
                    service=self.name,
                    status="empty",
                    sources=[]
                )
                
            sources = self._parse_results(results)
            
            if not sources:
                 return ServiceResult(
                    service=self.name,
                    status="empty",
                    sources=[]
                )
                 
            return ServiceResult(
                service=self.name,
                status="ok",
                sources=sources
            )
            
        except httpx.HTTPStatusError as e:
            error_msg = str(e).replace(api_key, "***")
            return ServiceResult(
                service=self.name,
                status="error",
                error=f"HTTP Error: {e.response.status_code} - {error_msg}"
            )
        except Exception as e:
            error_msg = str(e).replace(api_key, "***")
            return ServiceResult(
                service=self.name,
                status="error",
                error=f"Request failed: {error_msg}"
            )
