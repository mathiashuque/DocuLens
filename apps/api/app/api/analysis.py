"""Analysis HTTP routes: thin validation/dispatch, safe error mapping.

Error mapping matches classification's: 404/409/502/503 map identically,
since analysis's own eligibility check, and any classification call it makes
on the way, raise the same typed errors classification's route already
handles.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent.analysis.result import AnalysisFailedError
from agent.classification.classifier import ClassificationFailedError
from agent.classification.provider import ProviderRequestError, ProviderUnavailableError
from app.db.session import get_session
from app.schemas.analysis import AnalysisResponse
from app.services.analysis import (
    AnalysisNotFoundError,
    DocumentNotFoundError,
    TextlessDocumentError,
    analyze,
    get_latest_analysis,
)
from app.services.quota import require_anonymous_identity

router = APIRouter(prefix="/api/documents")


@router.post(
    "/{document_id}/analysis",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
async def analyze_document_route(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    quota_identity: str | None = Depends(require_anonymous_identity),
) -> AnalysisResponse:
    try:
        analysis = await analyze(document_id, session, quota_identity=quota_identity)
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.") from exc
    except TextlessDocumentError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Document has no extracted text available to analyze.",
        ) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Analysis provider is unavailable.",
        ) from exc
    except (
        ProviderRequestError,
        ClassificationFailedError,
        AnalysisFailedError,
    ) as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Analysis provider failed to produce a valid result.",
        ) from exc

    return AnalysisResponse.from_analysis(analysis)


@router.get(
    "/{document_id}/analysis",
    response_model=AnalysisResponse,
)
async def get_analysis_route(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> AnalysisResponse:
    try:
        analysis = await get_latest_analysis(document_id, session)
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.") from exc
    except AnalysisNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "No completed analysis exists."
        ) from exc

    return AnalysisResponse.from_analysis(analysis)
