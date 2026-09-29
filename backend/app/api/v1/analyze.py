"""API endpoints for text analysis."""

# FastAPI is provided by the backend environment; keep editor diagnostics from
# treating the application dependency as a missing local module.
# pyright: reportMissingImports=false
import logging

from fastapi import APIRouter, Depends

from app.schemas.request import AnalyzeRequest
from app.schemas.response import AnalyzeResponse, ServiceStatus, Source
from app.api.deps import verify_api_key

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(request: AnalyzeRequest, api_key: str = Depends(verify_api_key)):
    # Do not log user text content directly according to requirements
    logger.info(f"Received analysis request for platform {request.platform} with text length {len(request.text)}")
    
    # Mock data return
    return AnalyzeResponse(
        verdict="likely_false",
        confidence_score=0.85,
        explanation="This is a mock explanation. The claim is likely false based on known facts.",
        sources=[
            Source(
                title="Mock Source Title",
                url="https://example.com/factcheck",
                publisher="Mock Publisher",
                snippet="Mock snippet refuting the claim.",
                stance="refutes"
            )
        ],
        service_status=ServiceStatus(
            factcheck="ok",
            tavily="ok",
            gemini="ok"
        )
    )
