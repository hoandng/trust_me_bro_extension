import asyncio
from typing import List

from app.schemas.internal import AnalysisContext
from app.schemas.response import AnalyzeResponse, ServiceStatus, Source
from app.services.base_service import BaseService

class AnalysisOrchestrator:
    def __init__(self, services: List[BaseService]):
        self.services = services

    async def analyze(self, ctx: AnalysisContext) -> AnalyzeResponse:
        # Run all services concurrently
        tasks = [service.check(ctx) for service in self.services]
        results = await asyncio.gather(*tasks)

        # Aggregate results
        all_sources: List[Source] = []
        
        # Default status is empty for all expected services
        status_dict = {
            "factcheck": "empty",
            "tavily": "empty",
            "gemini": "empty"
        }

        for res in results:
            # Aggregate sources
            if res.sources:
                all_sources.extend(res.sources)
            
            # Update status if the service name matches one of the expected fields
            # or if we are using generic names in tests. 
            # We'll safely update if the key exists, otherwise we'll add it (which might violate pydantic model if strict, 
            # but we can map standard names, or if a service has a specific name we capture it).
            if res.service in status_dict:
                status_dict[res.service] = res.status
            else:
                # For tests that use FakeServices with different names, 
                # we might need to dynamically handle them, or tests should use valid names.
                # Let's map it back to ServiceStatus carefully.
                pass

        # Temporarily simple aggregation logic for verdict and explanation
        verdict = "unverified"
        explanation = "No sufficient data to verify."
        confidence_score = 0.0

        if any(r.status == "ok" for r in results):
            verdict = "likely_true"
            explanation = "Aggregated result based on successful service responses."
            confidence_score = 0.8
        elif any(r.status == "error" for r in results):
             verdict = "unverified"
             explanation = "Some services encountered errors during analysis."
             confidence_score = 0.0

        return AnalyzeResponse(
            verdict=verdict,
            confidence_score=confidence_score,
            explanation=explanation,
            sources=all_sources,
            service_status=ServiceStatus(**status_dict)
        )
