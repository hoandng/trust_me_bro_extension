import httpx
from typing import Optional, List, Dict, Any

from app.schemas.internal import AnalysisContext, ServiceResult
from app.schemas.response import Source
from app.services.base_service import BaseService, safe_execute
from app.core.config import settings

class FactCheckService(BaseService):
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        # Allow passing an existing client for lifespan reuse
        self._client = client or httpx.AsyncClient(timeout=10.0)
        
    @property
    def name(self) -> str:
        return "factcheck"
        
    async def aclose(self):
        if self._client:
            await self._client.aclose()

    def _determine_stance(self, rating: str) -> str:
        if not rating:
            return "neutral"
        r = rating.lower()
        if any(w in r for w in ["false", "fake", "pants on fire", "misleading", "incorrect", "untrue", "hoax"]):
            return "refutes"
        if "true" in r and "untrue" not in r and "half true" not in r and "mostly true" not in r:
            return "supports"
        if "mostly true" in r:
             return "supports"
        return "neutral"

    def _parse_claims(self, claims: List[Dict[str, Any]]) -> List[Source]:
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
                    sources.append(Source(
                        title=title,
                        url=url,
                        publisher=publisher_name,
                        snippet=rating,
                        stance=stance
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

        api_key = settings.factcheck_api_key
        if not api_key:
            return ServiceResult(
                service=self.name,
                status="error",
                error="FactCheck API key not configured"
            )

        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        
        # Try with language first if provided
        params = {
            "key": api_key,
            "query": query,
            "pageSize": 10
        }
        
        if ctx.lang:
            params["languageCode"] = ctx.lang

        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            claims = data.get("claims", [])
            
            # If empty and we used language code, retry without language code
            if not claims and ctx.lang:
                params.pop("languageCode", None)
                response = await self._client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                claims = data.get("claims", [])
                
            if not claims:
                return ServiceResult(
                    service=self.name,
                    status="empty",
                    sources=[]
                )
                
            sources = self._parse_claims(claims)
            
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
            # Mask API key in error message
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

