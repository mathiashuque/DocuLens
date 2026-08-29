"""Index and search HTTP routes: thin validation/dispatch, safe error
mapping. No delete/reindex, global search, or background jobs in this slice.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.retrieval import (
    IndexResponse,
    SearchRequest,
    SearchResponse,
    SearchResultResponse,
)
from app.services.indexing import (
    DocumentNotFoundError as IndexDocumentNotFoundError,
)
from app.services.indexing import (
    EmbeddingProviderRequestError,
    EmbeddingProviderUnavailableError,
    IneligibleDocumentError,
    index_document,
)
from app.services.indexing import (
    IncompatibleIndexError as IndexIncompatibleIndexError,
)
from app.services.search import (
    DocumentNotFoundError as SearchDocumentNotFoundError,
)
from app.services.search import (
    IncompatibleIndexError as SearchIncompatibleIndexError,
)
from app.services.search import (
    IndexNotFoundError,
    InvalidQueryError,
    search_document,
)
from retrieval.chunking import ChunkingError

router = APIRouter(prefix="/api/documents")


@router.post(
    "/{document_id}/index",
    response_model=IndexResponse,
)
async def index_document_route(
    document_id: uuid.UUID,
    response: Response,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> IndexResponse:
    try:
        index, created = await index_document(document_id, session)
    except IndexDocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.") from exc
    except (IneligibleDocumentError, ChunkingError) as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Document is not eligible for indexing.",
        ) from exc
    except IndexIncompatibleIndexError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "An existing index is incompatible with the current "
            "embedding configuration.",
        ) from exc
    except EmbeddingProviderUnavailableError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Embedding provider is unavailable.",
        ) from exc
    except EmbeddingProviderRequestError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Embedding provider failed to produce a valid result.",
        ) from exc

    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return IndexResponse.model_validate(index)


@router.post(
    "/{document_id}/search",
    response_model=SearchResponse,
)
async def search_document_route(
    document_id: uuid.UUID,
    request: SearchRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> SearchResponse:
    try:
        query, results = await search_document(
            document_id, request.query, request.top_k, session
        )
    except SearchDocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.") from exc
    except IndexNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "No completed index exists."
        ) from exc
    except InvalidQueryError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except SearchIncompatibleIndexError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The stored index is incompatible with the current "
            "embedding configuration.",
        ) from exc
    except EmbeddingProviderUnavailableError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Embedding provider is unavailable.",
        ) from exc
    except EmbeddingProviderRequestError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Embedding provider failed to produce a valid result.",
        ) from exc

    return SearchResponse(
        document_id=document_id,
        query=query,
        results=[SearchResultResponse(**r.__dict__) for r in results],
    )
