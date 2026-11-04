import logging
import time
from typing import Literal

from pydantic import BaseModel, Field, ValidationError
from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.response import Source, ModelUsage, ModelFallback
from app.services.gemini_model_pool import model_pool, quota_cooldown, GeminiQuotaExhausted
from app.prompts.gemini_prompts import EXTRACT_CLAIMS_PROMPT, ASSESS_PROMPT

logger = logging.getLogger(__name__)

class ClaimExtraction(BaseModel):
    main_claim: str = Field(description="The main verifiable claim extracted from the text.")
    search_queries: list[str] = Field(description="Up to 3 brief search queries to verify the claim.", max_length=3)
    detected_lang: str = Field(description="The detected language of the text.")
    is_checkable: bool = Field(description="False if it's personal opinion, a question, an ad, or not verifiable.")

class SourceStance(BaseModel):
    url: str = Field(description="The URL of the source.")
    stance: Literal["supports", "refutes", "neutral"] = Field(description="The stance of the source regarding the claim.")

class Assessment(BaseModel):
    verdict: Literal["likely_true", "likely_false", "mixed", "unverified"] = Field(description="The final verdict.")
    confidence_score: float = Field(description="Confidence score between 0.0 and 1.0.", ge=0.0, le=1.0)
    explanation: str = Field(description="Brief explanation in Vietnamese, max 120 words.")
    source_stances: list[SourceStance] = Field(description="List of sources used and their stances.")
    status: str = Field(default="ok", description="Status of the assessment, can be 'error'")

class GeminiService:
    def __init__(self):
        # We initialize the client if there's an API key
        if settings.gemini_api_key:
            self.client = genai.Client(api_key=settings.gemini_api_key, http_options=types.HttpOptions(
                # Handle quota fallback here instead of retrying a blocked model in the SDK.
                retry_options=types.HttpRetryOptions(attempts=0), timeout=15000
            ))
        else:
            self.client = None
            logger.warning("Gemini API key is missing.")
            
        self.select_model(None)

    def select_model(self, model: str | None):
        self.model = model or settings.gemini_model
        if self.model not in settings.available_gemini_models:
            raise ValueError("Model is not enabled")
        self.model_usage = ModelUsage(requested_model=self.model)

    async def _create(self, stage: str, **kwargs):
        models = settings.available_gemini_models
        start = models.index(self.model)
        candidates = models[start:] + models[:start]
        for model in candidates:
            if model_pool.remaining(model):
                self.model_usage.fallbacks.append(ModelFallback(stage=stage, model=model))
                continue
            try:
                # Thinking configuration differs between model generations.
                config = {"thinking_level": "low"} if model.startswith("gemini-3") else {}
                interaction = await self.client.aio.interactions.create(
                    model=model, generation_config=config, **kwargs
                )
                setattr(self.model_usage, f"{stage}_model", model)
                return interaction
            except Exception as error:
                # Interactions SDK versions use status_code/body; older SDKs use code/details.
                if getattr(error, 'status_code', getattr(error, 'code', None)) != 429:
                    raise
                model_pool.block(model, quota_cooldown(error))
                self.model_usage.fallbacks.append(ModelFallback(stage=stage, model=model))
                logger.warning("Gemini quota reached for model %s", model)
        raise GeminiQuotaExhausted(min(model_pool.remaining(model) or 1 for model in candidates))

    async def extract_claims(self, text: str, lang: str | None = None) -> ClaimExtraction | None:
        if not self.client:
            logger.error("Gemini API key not configured")
            return None
        
        start_time = time.monotonic()
        text_len = len(text)
        
        prompt = f"<post>\n{text}\n</post>"
        
        response_format = [{
            "type": "text",
            "mime_type": "application/json",
            "schema": ClaimExtraction.model_json_schema(),
        }]
        
        for attempt in range(2): # 1 retry
            try:
                interaction = await self._create(
                    "extraction",
                    system_instruction=EXTRACT_CLAIMS_PROMPT,
                    input=prompt,
                    response_format=response_format,
                )
                
                raw_output = interaction.output_text
                if raw_output:
                    result = ClaimExtraction.model_validate_json(raw_output)
                    
                    elapsed = int((time.monotonic() - start_time) * 1000)
                    logger.info(f"extract_claims done: len={text_len}, time={elapsed}ms, checkable={result.is_checkable}")
                    
                    return result
            except GeminiQuotaExhausted:
                raise
            except ValidationError as e:
                logger.warning(f"Validation error on attempt {attempt + 1}: {e}")
            except Exception as e:
                logger.error(f"Error in extract_claims on attempt {attempt + 1}: {e}")
                
        elapsed = int((time.monotonic() - start_time) * 1000)
        logger.error(f"extract_claims failed after 2 attempts. time={elapsed}ms")
        return None

    async def assess(self, text: str, claim: str, evidence: list[Source]) -> Assessment:
        start_time = time.monotonic()
        text_len = len(text)
        
        if not self.client:
            logger.error("Gemini API key not configured")
            return Assessment(
                verdict="unverified", 
                confidence_score=0.0, 
                explanation="Lỗi hệ thống: Chưa cấu hình Gemini API key.", 
                source_stances=[],
                status="error"
            )

        evidence_text = ""
        valid_urls = set()
        for i, src in enumerate(evidence):
            evidence_text += f"Source {i+1}:\nURL: {src.url}\nTitle: {src.title}\nSnippet: {src.snippet}\n\n"
            valid_urls.add(src.url)

        input_text = f"Claim to verify: {claim}\n\n<post>\n{text}\n</post>\n\nEvidence:\n{evidence_text}"

        response_format = [{
            "type": "text",
            "mime_type": "application/json",
            "schema": Assessment.model_json_schema(),
        }]

        for attempt in range(2):
            try:
                interaction = await self._create(
                    "assessment",
                    system_instruction=ASSESS_PROMPT,
                    input=input_text,
                    response_format=response_format,
                )

                raw_output = interaction.output_text
                if raw_output:
                    result = Assessment.model_validate_json(raw_output)
                    
                    # Filter out hallucinatory URLs
                    filtered_stances = [s for s in result.source_stances if s.url in valid_urls]
                    result.source_stances = filtered_stances

                    elapsed = int((time.monotonic() - start_time) * 1000)
                    logger.info(f"assess done: text_len={text_len}, time={elapsed}ms, verdict={result.verdict}")
                    
                    return result
            except GeminiQuotaExhausted:
                raise
            except ValidationError as e:
                logger.warning(f"Validation error on attempt {attempt + 1}: {e}")
            except Exception as e:
                logger.error(f"Error in assess on attempt {attempt + 1}: {e}")

        elapsed = int((time.monotonic() - start_time) * 1000)
        logger.error(f"assess failed after 2 attempts. time={elapsed}ms")
        return Assessment(
            verdict="unverified",
            confidence_score=0.0,
            explanation="Không thể phân tích kết quả từ mô hình AI.",
            source_stances=[],
            status="error"
        )
