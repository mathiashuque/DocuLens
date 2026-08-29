"""Classification HTTP routes: thin validation/dispatch, safe error mapping."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent.classification.classifier import ClassificationFailedError
from agent.classification.provider import ProviderRequestError, ProviderUnavailableError
from app.db.session import get_session
from app.schemas.classification import ClassificationResponse
from app.services.classification import (
    ClassificationNotFoundError,
    DocumentNotFoundError,
    TextlessDocumentError,
    classify,
    get_latest_classification,
)

router = APIRouter(prefix="/api/documents")


@router.post(
    "/{document_id}/classification",
    response_model=ClassificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def classify_document_route(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> ClassificationResponse:
    try:
        classification = await classify(document_id, session)
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.") from exc
    except TextlessDocumentError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Document has no extracted text available to classify.",
        ) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Classification provider is unavailable.",
        ) from exc
    except (ProviderRequestError, ClassificationFailedError) as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Classification provider failed to produce a valid result.",
        ) from exc

    return ClassificationResponse.model_validate(classification)


@router.get(
    "/{document_id}/classification",
    response_model=ClassificationResponse,
)
async def get_classification_route(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> ClassificationResponse:
    try:
        classification = await get_latest_classification(document_id, session)
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.") from exc
    except ClassificationNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "No completed classification exists."
        ) from exc

    return ClassificationResponse.model_validate(classification)
