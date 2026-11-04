from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=20, max_length=2000, description="The text to analyze")
    platform: Literal["facebook", "x", "reddit"] = Field(..., description="The platform where the text is from")
    page_url: str | None = None
    lang: str | None = None
    model_id: str | None = Field(default=None, max_length=100)

    @field_validator('model_id')
    @classmethod
    def validate_model_id(cls, value: str | None) -> str | None:
        from app.core.config import settings
        if value is not None and value not in settings.available_gemini_models:
            raise ValueError("Model is not enabled")
        return value

    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not (20 <= len(v.strip()) <= 2000):
            raise ValueError("Text length must be between 20 and 2000 characters")
        return v
