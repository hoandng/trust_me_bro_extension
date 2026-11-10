import asyncio

from app.core.config import MAX_SEARCH_QUERIES, settings
from app.core.source_ranking import rank_sources
from app.schemas.internal import AnalysisContext
from app.schemas.response import AnalyzeResponse, ServiceStatus, Source
from app.services.gemini_model_pool import GeminiQuotaExhausted


class AnalysisOrchestrator:
    def __init__(self, gemini_service, factcheck_service, tavily_service):
        self.gemini_service = gemini_service
        self.factcheck_service = factcheck_service
        self.tavily_service = tavily_service

    async def analyze(self, ctx: AnalysisContext) -> AnalyzeResponse:
        # Initial status
        status_dict = {"factcheck": "empty", "tavily": "empty", "gemini": "ok"}

        # Stage 0: Extract Claims
        try:
            extraction = await asyncio.wait_for(
                self.gemini_service.extract_claims(ctx.text, ctx.lang), timeout=20.0
            )
        except GeminiQuotaExhausted:
            raise
        except Exception:  # noqa: BLE001 - Keep degraded results without logging payloads.
            status_dict["gemini"] = "error"
            return AnalyzeResponse(
                verdict="unverified",
                confidence_score=0.0,
                explanation="Lỗi khi phân tích nội dung. Không thể trích xuất thông tin.",
                sources=[],
                service_status=ServiceStatus(**status_dict),
            )

        if not extraction:
            status_dict["gemini"] = "error"
            return AnalyzeResponse(
                verdict="unverified",
                confidence_score=0.0,
                explanation="Không thể phân tích văn bản do lỗi dịch vụ.",
                sources=[],
                service_status=ServiceStatus(**status_dict),
            )

        if not extraction.is_checkable:
            return AnalyzeResponse(
                verdict="unverified",
                confidence_score=0.0,
                explanation="Nội dung là ý kiến cá nhân, câu hỏi hoặc không chứa thông tin có thể kiểm chứng được.",
                sources=[],
                service_status=ServiceStatus(**status_dict),
            )

        # Update ctx with extraction results
        ctx.claim = extraction.main_claim
        ctx.search_queries = extraction.search_queries
        ctx.lang = extraction.detected_lang

        # Tối đa hai query, hai provider và một fallback cho mỗi cặp.
        query_limit = min(settings.search_query_limit, MAX_SEARCH_QUERIES)
        queries = dict.fromkeys(
            query.strip()
            for query in extraction.search_queries[:query_limit]
            if query.strip()
        )
        if not queries and (claim := extraction.main_claim.strip()):
            queries[claim] = None

        providers = {"factcheck": self.factcheck_service, "tavily": self.tavily_service}
        jobs = [
            (name, service.check(ctx.model_copy(update={"search_queries": [query]})))
            for name, service in providers.items()
            for query in queries
        ]
        sources_by_provider: dict[str, list[Source]] = {name: [] for name in providers}
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*(job for _, job in jobs), return_exceptions=True),
                timeout=15.0,
            )
        except TimeoutError:
            results = [TimeoutError() for _ in jobs]

        for (name, _), result in zip(jobs, results, strict=True):
            if isinstance(result, BaseException):
                status_dict[name] = "error"
                continue
            sources_by_provider[name].extend(result.sources)
            if result.status == "error" or status_dict[name] == "empty":
                status_dict[name] = result.status

        factcheck_sources = sources_by_provider["factcheck"]
        tavily_sources = sources_by_provider["tavily"]
        unique_sources = {}
        for source in (*factcheck_sources, *tavily_sources):
            unique_sources.setdefault(source.url, source)
        sorted_sources = [
            source.model_copy(deep=True)
            for source in rank_sources(list(unique_sources.values()))[:8]
        ]

        # If both FactCheck and Tavily are empty/error
        if not sorted_sources:
            return AnalyzeResponse(
                verdict="unverified",
                confidence_score=0.3,
                explanation="Không tìm thấy đủ bằng chứng để xác minh thông tin này.",
                sources=[],
                service_status=ServiceStatus(**status_dict),
            )

        # Stage 2: Gemini Assess
        try:
            assessment = await asyncio.wait_for(
                self.gemini_service.assess(ctx.text, ctx.claim, sorted_sources),
                timeout=20.0,
            )
        except GeminiQuotaExhausted:
            raise
        except Exception:  # noqa: BLE001 - Keep degraded results without logging payloads.
            status_dict["gemini"] = "error"
            return AnalyzeResponse(
                verdict="unverified",
                confidence_score=0.0,
                explanation="Lỗi khi đánh giá bằng chứng thu thập được.",
                sources=sorted_sources,
                service_status=ServiceStatus(**status_dict),
            )

        if assessment.status == "error":
            status_dict["gemini"] = "error"

        factcheck_urls = {s.url for s in factcheck_sources}
        tavily_urls = {s.url for s in tavily_sources}
        if assessment.source_stances:
            stance_map = {st.url: st.stance for st in assessment.source_stances}
            for s in sorted_sources:
                if (
                    s.url in tavily_urls
                    and s.url not in factcheck_urls
                    and s.url in stance_map
                ):
                    s.stance = stance_map[s.url]

        # Rule: If FactCheck has clear results, prioritize it
        verdict = assessment.verdict
        confidence_score = assessment.confidence_score

        factcheck_clear_supports = False
        factcheck_clear_refutes = False

        match_map = {st.url: st.factcheck_match for st in assessment.source_stances}
        if assessment.status != "error":
            assessed_urls = {s.url for s in sorted_sources}
            for s in factcheck_sources[:1]:
                if (
                    s.url not in assessed_urls
                    or not s.claim_text
                    or not s.claim_text.strip()
                    or match_map.get(s.url) is not True
                ):
                    continue
                if s.original_stance == "supports":
                    factcheck_clear_supports = True
                elif s.original_stance == "refutes":
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
            service_status=ServiceStatus(**status_dict),
        )
