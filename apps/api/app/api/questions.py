"""Grounded single-document question-answering HTTP route: thin
validation/dispatch, safe error mapping. No chat, conversation history, or
persistence in this slice."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.grounded_qa import (
    AnsweredResponse,
    CitationResponse,
    InsufficientEvidenceResponse,
    QuestionRequest,
    QuestionResponse,
)
from app.services.grounded_qa import (
    AnsweredResult,
    DocumentNotFoundError,
    IncompatibleIndexError,
    IndexNotFoundError,
    InvalidQueryError,
    InvalidQuestionError,
    ProviderRequestError,
    ProviderUnavailableError,
    answer_question,
)

router = APIRouter(prefix="/api/documents")


@router.post(
    "/{document_id}/questions",
    response_model=QuestionResponse,
)
async def ask_question_route(
    document_id: uuid.UUID,
    request: QuestionRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> QuestionResponse:
    try:
        result = await answer_question(
            document_id, request.question, request.top_k, session
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.") from exc
    except IndexNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "No completed index exists."
        ) from exc
    except (InvalidQuestionError, InvalidQueryError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except IncompatibleIndexError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The stored index is incompatible with the current "
            "embedding configuration.",
        ) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Generation provider is unavailable.",
        ) from exc
    except ProviderRequestError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Generation provider failed to produce a valid result.",
        ) from exc

    citations = [
        CitationResponse(chunk_id=c.chunk_id, page=c.page, evidence=c.evidence)
        for c in result.citations
    ]
    if isinstance(result, AnsweredResult):
        return AnsweredResponse(
            document_id=document_id,
            question=request.question,
            answer=result.answer,
            citations=citations,
        )
    return InsufficientEvidenceResponse(
        document_id=document_id,
        question=request.question,
        answer=result.answer,
        citations=citations,
    )
