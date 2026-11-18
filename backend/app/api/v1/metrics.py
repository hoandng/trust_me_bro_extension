from typing import Annotated, Literal

from app.api.deps import authenticate_admin, get_metrics_store, verify_api_key
from app.core.metrics import MetricsStore
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import UUID4, BaseModel, ConfigDict, StrictBool

router = APIRouter()


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID4
    helpful: StrictBool
    reason: (
        Literal["incorrect_verdict", "missing_context", "weak_sources", "other"] | None
    ) = None


@router.post("/feedback", status_code=204, dependencies=[Depends(verify_api_key)])
def submit_feedback(
    feedback: FeedbackRequest,
    store: Annotated[MetricsStore, Depends(get_metrics_store)],
) -> Response:
    if not store.save_feedback(
        str(feedback.request_id), feedback.helpful, feedback.reason
    ):
        raise HTTPException(status_code=404, detail="Analysis result not found")
    return Response(status_code=204)


@router.get("/stats/summary", dependencies=[Depends(authenticate_admin)])
def stats_summary(store: Annotated[MetricsStore, Depends(get_metrics_store)]) -> dict:
    return store.summary()
