from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=20, max_length=2000, description="The text to analyze")
    platform: Literal["facebook", "x", "reddit"] = Field(..., description="The platform where the text is from")
    page_url: str | None = None
    lang: str | None = None

    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not (20 <= len(v.strip()) <= 2000):
            raise ValueError("Text length must be between 20 and 2000 characters")
        return v
