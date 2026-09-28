from typing import Literal

from pydantic import BaseModel


class Source(BaseModel):
    title: str
    url: str
    publisher: str | None = None
    snippet: str | None = None
    stance: Literal["supports", "refutes", "neutral"] | None = None

class ServiceStatus(BaseModel):
    factcheck: Literal["ok", "error", "empty"]
    tavily: Literal["ok", "error", "empty"]
    gemini: Literal["ok", "error", "empty"]

class AnalyzeResponse(BaseModel):
    verdict: Literal["likely_true", "likely_false", "mixed", "unverified"]
    confidence_score: float
    explanation: str
    sources: list[Source]
    service_status: ServiceStatus
