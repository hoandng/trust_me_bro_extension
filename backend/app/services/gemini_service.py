import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.core.metrics import GeminiUsage, current_metrics
from app.core.source_ranking import source_tier
from app.prompts.gemini_prompts import ASSESS_PROMPT, EXTRACT_CLAIMS_PROMPT
from app.schemas.response import ModelFallback, ModelUsage, Source
from app.services.gemini_model_pool import (
    GeminiQuotaExhausted,
    model_pool,
    quota_cooldown,
)

logger = logging.getLogger(__name__)
VIETNAM_TIMEZONE = timezone(timedelta(hours=7), "Asia/Ho_Chi_Minh")


class ClaimExtraction(BaseModel):
    main_claim: str = Field(
        description="The main verifiable claim extracted from the text."
    )
    search_queries: list[str] = Field(
        description="Up to 3 brief search queries to verify the claim.", max_length=3
    )
    detected_lang: str = Field(description="The detected language of the text.")
    is_checkable: bool = Field(
        description="False if it's personal opinion, a question, an ad, or not verifiable."
    )


class SourceStance(BaseModel):
    url: str = Field(description="The URL of the source.")
    stance: Literal["supports", "refutes", "neutral"] = Field(
        description="The stance of the source regarding the claim."
    )
    factcheck_match: bool = Field(
        default=False,
        strict=True,
        description="True only when the FactCheck claim matches the user's claim; false for Tavily or uncertain matches.",
    )


class Assessment(BaseModel):
    verdict: Literal["likely_true", "likely_false", "mixed", "unverified"] = Field(
        description="The final verdict."
    )
    confidence_score: float = Field(
        description="Confidence score between 0.0 and 1.0.", ge=0.0, le=1.0
    )
    explanation: str = Field(
        description="Brief explanation in Vietnamese, max 120 words."
    )
    source_stances: list[SourceStance] = Field(
        description="List of sources used and their stances."
    )
    status: str = Field(
        default="ok", description="Status of the assessment, can be 'error'"
    )


class GeminiService:
    def __init__(self):
        # We initialize the client if there's an API key
        if settings.gemini_api_key:
            self.client = genai.Client(
                api_key=settings.gemini_api_key,
                http_options=types.HttpOptions(
                    # Handle quota fallback here instead of retrying a blocked model in the SDK.
                    retry_options=types.HttpRetryOptions(attempts=0),
                    timeout=15000,
                ),
            )
        else:
            self.client = None
            logger.warning("Gemini API key is missing.")

    async def aclose(self) -> None:
        if self.client is not None:
            try:
                await self.client.aio.aclose()
            finally:
                self.client.close()

    async def _create(self, stage: str, model_usage: ModelUsage, **kwargs):
        models = settings.available_gemini_models
        start = models.index(model_usage.requested_model)
        candidates = models[start:] + models[:start]
        for model in candidates:
            if model_pool.remaining(model):
                model_usage.fallbacks.append(ModelFallback(stage=stage, model=model))
                continue
            try:
                # Thinking configuration differs between model generations.
                config = (
                    {"thinking_level": "low"} if model.startswith("gemini-3") else {}
                )
                metrics = current_metrics.get()
                attempt = None
                if metrics is not None:
                    attempt = GeminiUsage(model=model)
                    metrics.gemini_usage.append(attempt)
                interaction = await self.client.aio.interactions.create(
                    model=model, generation_config=config, store=False, **kwargs
                )
                if attempt is not None:
                    attempt.record(getattr(interaction, "usage", None))
                setattr(model_usage, f"{stage}_model", model)
                return interaction
            except Exception as error:
                # Interactions SDK versions use status_code/body; older SDKs use code/details.
                if getattr(error, "status_code", getattr(error, "code", None)) != 429:
                    raise
                model_pool.block(model, quota_cooldown(error))
                model_usage.fallbacks.append(ModelFallback(stage=stage, model=model))
                logger.warning("Gemini quota reached for model %s", model)
        raise GeminiQuotaExhausted(
            min(model_pool.remaining(model) or 1 for model in candidates)
        )

    async def extract_claims(
        self,
        text: str,
        lang: str | None = None,
        *,
        model_usage: ModelUsage | None = None,
    ) -> ClaimExtraction | None:
        if not self.client:
            logger.error("Gemini API key not configured")
            return None

        model_usage = model_usage or ModelUsage(requested_model=settings.gemini_model)

        prompt = f"<post>\n{text}\n</post>"

        response_format = [
            {
                "type": "text",
                "mime_type": "application/json",
                "schema": ClaimExtraction.model_json_schema(),
            }
        ]

        for attempt in range(2):  # 1 retry
            try:
                interaction = await self._create(
                    "extraction",
                    model_usage,
                    system_instruction=EXTRACT_CLAIMS_PROMPT,
                    input=prompt,
                    response_format=response_format,
                )

                raw_output = interaction.output_text
                if raw_output:
                    return ClaimExtraction.model_validate_json(raw_output)
            except GeminiQuotaExhausted:
                raise
            except ValidationError:
                logger.warning("Validation error on attempt %s", attempt + 1)
            except Exception:  # noqa: BLE001 - Keep degraded results without logging payloads.
                logger.error("Error in extract_claims on attempt %s", attempt + 1)

        logger.error("extract_claims failed after 2 attempts")
        return None

    async def assess(
        self,
        text: str,
        claim: str,
        evidence: list[Source],
        *,
        model_usage: ModelUsage | None = None,
    ) -> Assessment:
        if not self.client:
            logger.error("Gemini API key not configured")
            return Assessment(
                verdict="unverified",
                confidence_score=0.0,
                explanation="Lỗi hệ thống: Chưa cấu hình Gemini API key.",
                source_stances=[],
                status="error",
            )

        model_usage = model_usage or ModelUsage(requested_model=settings.gemini_model)
        evidence_text = ""
        valid_urls = set()
        for i, src in enumerate(evidence):
            evidence_text += (
                f"Source {i + 1}:\nURL: {src.url}\nTitle: {src.title}\nSnippet: {src.snippet}\n"
                f"Source tier: {source_tier(src.url)}\n"
                f"Published date: {src.published_date or 'unknown'}\n"
                f"Source type: {'factcheck' if src.original_stance is not None else 'tavily'}\n"
                f"FactCheck claim: {src.claim_text}\n"
                f"Original stance: {src.original_stance}\n\n"
            )
            valid_urls.add(src.url)

        today = datetime.now(VIETNAM_TIMEZONE).date().isoformat()
        input_text = (
            f"Current date (Asia/Ho_Chi_Minh): {today}\n"
            f"Claim to verify: {claim}\n\n<post>\n{text}\n</post>\n\nEvidence:\n{evidence_text}"
        )

        response_format = [
            {
                "type": "text",
                "mime_type": "application/json",
                "schema": Assessment.model_json_schema(),
            }
        ]

        for attempt in range(2):
            try:
                interaction = await self._create(
                    "assessment",
                    model_usage,
                    system_instruction=ASSESS_PROMPT,
                    input=input_text,
                    response_format=response_format,
                )

                raw_output = interaction.output_text
                if raw_output:
                    result = Assessment.model_validate_json(raw_output)

                    # Filter out hallucinatory URLs
                    filtered_stances = [
                        s for s in result.source_stances if s.url in valid_urls
                    ]
                    result.source_stances = filtered_stances

                    return result
            except GeminiQuotaExhausted:
                raise
            except ValidationError:
                logger.warning("Validation error on attempt %s", attempt + 1)
            except Exception:  # noqa: BLE001 - Keep degraded results without logging payloads.
                logger.error("Error in assess on attempt %s", attempt + 1)

        logger.error("assess failed after 2 attempts")
        return Assessment(
            verdict="unverified",
            confidence_score=0.0,
            explanation="Không thể phân tích kết quả từ mô hình AI.",
            source_stances=[],
            status="error",
        )
