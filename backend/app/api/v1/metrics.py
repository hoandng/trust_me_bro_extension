import logging
import re
import unicodedata
from typing import Annotated, Literal

from app.api.deps import authenticate_admin, get_metrics_store, verify_api_key
from app.core.metrics import MetricsStore
from fastapi import APIRouter, Depends, HTTPException
from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)
from starlette.concurrency import run_in_threadpool

router = APIRouter()
logger = logging.getLogger(__name__)
FEEDBACK_COMMENT_MAX_LENGTH = 500


def _normalize_comment(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFC", value)
    without_ctrl = "".join(
        ch
        for ch in normalized
        if ch in ("\n", "\t") or not unicodedata.category(ch).startswith("C")
    )
    collapsed = re.sub(r"[ \t]+", " ", without_ctrl).strip()
    if not collapsed:
        return None
    if len(collapsed) > FEEDBACK_COMMENT_MAX_LENGTH:
        raise ValueError(
            f"Comment must be at most {FEEDBACK_COMMENT_MAX_LENGTH} characters"
        )
    return collapsed


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID4
    rating: StrictInt | None = None
    comment: str | None = None
    helpful: StrictBool | None = None
    reason: (
        Literal["incorrect_verdict", "missing_context", "weak_sources", "other"] | None
    ) = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, value: int | None) -> int | None:
        if value is not None and not (1 <= value <= 5):
            raise ValueError("Rating must be between 1 and 5")
        return value

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, value: str | None) -> str | None:
        return _normalize_comment(value)

    @model_validator(mode="after")
    def validate_choice(self) -> "FeedbackRequest":
        has_rating = self.rating is not None
        has_helpful = self.helpful is not None
        if has_rating == has_helpful:
            raise ValueError("Provide exactly one of rating or helpful")
        if has_helpful and self.comment is not None:
            raise ValueError("comment is only valid with rating")
        if has_rating and self.reason is not None:
            raise ValueError("reason is only valid with helpful")
        return self


@router.post("/feedback", status_code=200, dependencies=[Depends(verify_api_key)])
async def submit_feedback(
    feedback: FeedbackRequest,
    store: Annotated[MetricsStore, Depends(get_metrics_store)],
) -> dict[str, str]:
    status_result = await run_in_threadpool(
        store.save_feedback,
        str(feedback.request_id),
        rating=feedback.rating,
        comment=feedback.comment,
        helpful=feedback.helpful,
        reason=feedback.reason,
    )
    if status_result == "not_found":
        raise HTTPException(status_code=404, detail="Analysis result not found")
    if status_result == "conflict":
        raise HTTPException(status_code=409, detail="Feedback already submitted")

    logger.info(
        "feedback_saved request_id=%s rating=%s comment_length=%d",
        feedback.request_id,
        feedback.rating,
        len(feedback.comment) if feedback.comment else 0,
    )
    return {"status": "ok"}


@router.get("/stats/summary", dependencies=[Depends(authenticate_admin)])
async def stats_summary(
    store: Annotated[MetricsStore, Depends(get_metrics_store)],
) -> dict:
    return await run_in_threadpool(store.summary)
