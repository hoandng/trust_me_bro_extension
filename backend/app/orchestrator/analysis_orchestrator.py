import asyncio
from app.services.gemini_model_pool import GeminiQuotaExhausted
from typing import List

from app.schemas.internal import AnalysisContext
from app.schemas.response import AnalyzeResponse, ServiceStatus, Source
from app.services.base_service import BaseService

class AnalysisOrchestrator:
    def __init__(
        self,
        gemini_service,
        factcheck_service,
        tavily_service
    ):
        self.gemini_service = gemini_service
        self.factcheck_service = factcheck_service
        self.tavily_service = tavily_service

    async def analyze(self, ctx: AnalysisContext) -> AnalyzeResponse:
        # Initial status
        status_dict = {
            "factcheck": "empty",
            "tavily": "empty",
            "gemini": "ok"
        }

        # Stage 0: Extract Claims
        try:
            extraction = await asyncio.wait_for(
                self.gemini_service.extract_claims(ctx.text, ctx.lang),
                timeout=20.0
            )
        except GeminiQuotaExhausted:
            raise
        except Exception as e:
            status_dict["gemini"] = "error"
            return AnalyzeResponse(
                verdict="unverified",
                confidence_score=0.0,
                explanation="Lỗi khi phân tích nội dung. Không thể trích xuất thông tin.",
                sources=[],
                service_status=ServiceStatus(**status_dict)
            )

        if not extraction:
            status_dict["gemini"] = "error"
            return AnalyzeResponse(
                verdict="unverified",
                confidence_score=0.0,
                explanation="Không thể phân tích văn bản do lỗi dịch vụ.",
                sources=[],
                service_status=ServiceStatus(**status_dict)
            )

        if not extraction.is_checkable:
            return AnalyzeResponse(
                verdict="unverified",
                confidence_score=0.0,
                explanation="Nội dung là ý kiến cá nhân, câu hỏi hoặc không chứa thông tin có thể kiểm chứng được.",
                sources=[],
                service_status=ServiceStatus(**status_dict)
            )

        # Update ctx with extraction results
        ctx.claim = extraction.main_claim
        ctx.search_queries = extraction.search_queries
        ctx.lang = extraction.detected_lang

        # Stage 1: FactCheck + Tavily concurrently
        tasks = [
            self.factcheck_service.check(ctx),
            self.tavily_service.check(ctx)
        ]
        
        try:
            # Overall timeout for Stage 1 & 2 is around 15s (25s total)
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=15.0
            )
        except asyncio.TimeoutError:
            results = [Exception("Timeout"), Exception("Timeout")]

        all_sources = []
        factcheck_res = None
        tavily_res = None

        # Extract results
        for i, service_name in enumerate(["factcheck", "tavily"]):
            res = results[i]
            if isinstance(res, Exception):
                status_dict[service_name] = "error"
            else:
                status_dict[service_name] = res.status
                if res.sources:
                    all_sources.extend(res.sources)
                if service_name == "factcheck":
                    factcheck_res = res
                else:
                    tavily_res = res

        # Sort sources: factcheck first, then remove duplicate URLs, max 8
        unique_urls = set()
        sorted_sources = []
        
        # Add factcheck sources first
        if factcheck_res and factcheck_res.sources:
            for s in factcheck_res.sources:
                if s.url not in unique_urls:
                    unique_urls.add(s.url)
                    sorted_sources.append(s)
                    
        # Add tavily sources next
        if tavily_res and tavily_res.sources:
            for s in tavily_res.sources:
                if s.url not in unique_urls:
                    unique_urls.add(s.url)
                    sorted_sources.append(s)

        sorted_sources = sorted_sources[:8]

        # If both FactCheck and Tavily are empty/error
        if not sorted_sources:
            return AnalyzeResponse(
                verdict="unverified",
                confidence_score=0.3,
                explanation="Không tìm thấy đủ bằng chứng để xác minh thông tin này.",
                sources=[],
                service_status=ServiceStatus(**status_dict)
            )

        # Stage 2: Gemini Assess
        try:
            assessment = await asyncio.wait_for(
                self.gemini_service.assess(ctx.text, ctx.claim, sorted_sources),
                timeout=20.0
            )
        except GeminiQuotaExhausted:
            raise
        except Exception:
            status_dict["gemini"] = "error"
            return AnalyzeResponse(
                verdict="unverified",
                confidence_score=0.0,
                explanation="Lỗi khi đánh giá bằng chứng thu thập được.",
                sources=sorted_sources,
                service_status=ServiceStatus(**status_dict)
            )

        if assessment.status == "error":
            status_dict["gemini"] = "error"

        if assessment.source_stances:
            stance_map = {st.url: st.stance for st in assessment.source_stances}
            for s in sorted_sources:
                if s.url in stance_map:
                    s.stance = stance_map[s.url]

        # Rule: If FactCheck has clear results, prioritize it
        verdict = assessment.verdict
        confidence_score = assessment.confidence_score
        
        factcheck_clear_supports = False
        factcheck_clear_refutes = False
        
        if factcheck_res and factcheck_res.sources:
            for s in factcheck_res.sources[:1]: # Check top factcheck
                if s.stance == "supports":
                    factcheck_clear_supports = True
                elif s.stance == "refutes":
                    factcheck_clear_refutes = True

        if factcheck_clear_supports and verdict != "likely_true":
            verdict = "likely_true"
            confidence_score = max(confidence_score, 0.8)
        elif factcheck_clear_refutes and verdict != "likely_false":
            verdict = "likely_false"
            confidence_score = max(confidence_score, 0.8)

        # Ensure consistency
        if verdict in ["likely_true", "likely_false"] and confidence_score < 0.5:
            confidence_score = 0.5
        elif verdict == "unverified":
            confidence_score = min(confidence_score, 0.4)

        return AnalyzeResponse(
            verdict=verdict,
            confidence_score=confidence_score,
            explanation=assessment.explanation,
            sources=sorted_sources,
            service_status=ServiceStatus(**status_dict)
        )
