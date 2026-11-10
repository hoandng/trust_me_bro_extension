from typing import Literal

from pydantic import BaseModel, Field


class Source(BaseModel):
    title: str
    url: str
    publisher: str | None = None
    snippet: str | None = None
    stance: Literal["supports", "refutes", "neutral"] | None = None
    original_stance: Literal["supports", "refutes", "neutral"] | None = Field(
        default=None, frozen=True
    )
    claim_text: str | None = None
    published_date: str | None = None


class ServiceStatus(BaseModel):
    factcheck: Literal["ok", "error", "empty"]
    tavily: Literal["ok", "error", "empty"]
    gemini: Literal["ok", "error", "empty"]


class ModelFallback(BaseModel):
    stage: str
    model: str
    reason: str = "quota"


class ModelUsage(BaseModel):
    requested_model: str
    extraction_model: str | None = None
    assessment_model: str | None = None
    fallbacks: list[ModelFallback] = []


class AnalyzeResponse(BaseModel):
    verdict: Literal["likely_true", "likely_false", "mixed", "unverified"]
    confidence_score: float
    explanation: str
    sources: list[Source]
    service_status: ServiceStatus
    model_usage: ModelUsage | None = None
