import json
import logging
import time
from typing import Literal, Any

from pydantic import BaseModel, Field, ValidationError
from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.response import Source
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
            self.client = genai.Client(api_key=settings.gemini_api_key)
        else:
            self.client = None
            logger.warning("Gemini API key is missing.")
            
        self.model = settings.gemini_model

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
                interaction = await self.client.aio.interactions.create(
                    model=self.model,
                    system_instruction=EXTRACT_CLAIMS_PROMPT,
                    input=prompt,
                    response_format=response_format,
                    generation_config={"thinking_level": "low"},
                )
                
                raw_output = interaction.output_text
                if raw_output:
                    result = ClaimExtraction.model_validate_json(raw_output)
                    
                    elapsed = int((time.monotonic() - start_time) * 1000)
                    logger.info(f"extract_claims done: len={text_len}, time={elapsed}ms, checkable={result.is_checkable}")
                    
                    return result
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
                interaction = await self.client.aio.interactions.create(
                    model=self.model,
                    system_instruction=ASSESS_PROMPT,
                    input=input_text,
                    response_format=response_format,
                    generation_config={"thinking_level": "low"},
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
