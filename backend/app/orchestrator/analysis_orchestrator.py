import asyncio
import logging
from contextlib import contextmanager

from app.core.config import MAX_SEARCH_QUERIES, settings
from app.core.source_ranking import rank_sources
from app.schemas.internal import AnalysisContext
from app.schemas.response import AnalyzeResponse, ModelUsage, ServiceStatus, Source
from app.services.gemini_model_pool import GeminiQuotaExhausted

logger = logging.getLogger(__name__)
TIMEOUT_EXPLANATION = (
    "Đã hết thời gian phân tích. Chưa đủ cơ sở để xác minh thông tin này."
)


class _AnalysisTiming:
    def __init__(self):
        self.clock = asyncio.get_running_loop().time
        self.started = self.clock()
        self.deadline = self.started + settings.analysis_timeout_seconds
        self.metadata = {
            "extract_ms": None,
            "evidence_ms": None,
            "assess_ms": None,
            "timeout_stage": None,
        }

    @contextmanager
    def stage(self, name: str):
        started = self.clock()
        try:
            yield
        except TimeoutError:
            self.metadata["timeout_stage"] = name
            raise
        finally:
            self.metadata[f"{name}_ms"] = round((self.clock() - started) * 1000)

    def log(self):
        logger.info(
            "analysis_timing",
            extra={
                **self.metadata,
                "total_ms": round((self.clock() - self.started) * 1000),
            },
        )


class AnalysisOrchestrator:
    def __init__(self, gemini_service, factcheck_service, tavily_service):
        self.gemini_service = gemini_service
        self.factcheck_service = factcheck_service
        self.tavily_service = tavily_service

    async def analyze(
        self, ctx: AnalysisContext, *, model_id: str | None = None
    ) -> AnalyzeResponse:
        timing = _AnalysisTiming()
        model_usage = ModelUsage(requested_model=model_id or settings.gemini_model)
        try:
            response = await self._analyze(ctx, model_usage, timing)
            response.model_usage = model_usage
            return response
        finally:
            timing.log()

    async def _analyze(
        self, ctx: AnalysisContext, model_usage: ModelUsage, timing: _AnalysisTiming
    ) -> AnalyzeResponse:
        # Initial status
        status_dict = {"factcheck": "empty", "tavily": "empty", "gemini": "ok"}

        # Stage 0: Extract Claims
        try:
            with timing.stage("extract"):
                async with asyncio.timeout_at(
                    min(timing.deadline, timing.clock() + 20)
                ):
                    extraction = await self.gemini_service.extract_claims(
                        ctx.text, ctx.lang, model_usage=model_usage
                    )
        except GeminiQuotaExhausted:
            raise
        except Exception:  # noqa: BLE001 - Keep degraded results without logging payloads.
            status_dict["gemini"] = "error"
            return AnalyzeResponse(
                verdict="unverified",
                confidence_score=0.0,
                explanation=(
                    TIMEOUT_EXPLANATION
                    if timing.metadata["timeout_stage"] == "extract"
                    else "Lỗi khi phân tích nội dung. Không thể trích xuất thông tin."
                ),
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
        sources_by_provider: dict[str, list[Source]] = {name: [] for name in providers}
        with timing.stage("evidence"):
            remaining = timing.deadline - timing.clock()
            jobs = (
                [
                    (
                        name,
                        asyncio.create_task(
                            service.check(
                                ctx.model_copy(update={"search_queries": [query]})
                            )
                        ),
                    )
                    for name, service in providers.items()
                    for query in queries
                ]
                if remaining > 0
                else []
            )
            if jobs:
                tasks = [task for _, task in jobs]
                try:
                    _, pending = await asyncio.wait(tasks, timeout=min(remaining, 15.0))
                    if pending:
                        timing.metadata["timeout_stage"] = "evidence"
                finally:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    results = await asyncio.gather(*tasks, return_exceptions=True)
            else:
                results = []

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

        if timing.clock() >= timing.deadline:
            timing.metadata["timeout_stage"] = "evidence"
            if sorted_sources:
                status_dict["gemini"] = "error"
            return AnalyzeResponse(
                verdict="unverified",
                confidence_score=0.0,
                explanation=TIMEOUT_EXPLANATION,
                sources=sorted_sources,
                service_status=ServiceStatus(**status_dict),
            )

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
            with timing.stage("assess"):
                async with asyncio.timeout_at(
                    min(timing.deadline, timing.clock() + 20)
                ):
                    assessment = await self.gemini_service.assess(
                        ctx.text, ctx.claim, sorted_sources, model_usage=model_usage
                    )
        except GeminiQuotaExhausted:
            raise
        except Exception:  # noqa: BLE001 - Keep degraded results without logging payloads.
            status_dict["gemini"] = "error"
            return AnalyzeResponse(
                verdict="unverified",
                confidence_score=0.0,
                explanation=(
                    TIMEOUT_EXPLANATION
                    if timing.metadata["timeout_stage"] == "assess"
                    else "Lỗi khi đánh giá bằng chứng thu thập được."
                ),
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
