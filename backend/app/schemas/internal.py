from typing import Literal

from pydantic import BaseModel
from .response import Source

class AnalysisContext(BaseModel):
    text: str
    lang: str | None = None
    claim: str | None = None
    search_queries: list[str] | None = None

class ServiceResult(BaseModel):
    service: str
    status: Literal["ok", "error", "empty"]
    sources: list[Source] = []
    raw_summary: str | None = None
    error: str | None = None
    duration_ms: int = 0
