"""Document upload, parsing, and persistence HTTP routes."""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import UploadSettings, load_upload_settings
from app.db.session import get_session
from app.schemas.document import (
    DocumentPageResponse,
    DocumentResponse,
    ParseDocumentResponse,
)
from app.services.document_parsing import (
    UnsupportedFileTypeError,
    UploadTooLargeError,
    read_and_parse_pdf,
)
from app.services.document_persistence import (
    DocumentNotFoundError,
    create_document,
    get_document,
)
from ingestion.errors import (
    EncryptedDocumentError,
    MalformedDocumentError,
    PageLimitExceededError,
)

router = APIRouter(prefix="/api/documents")


def _raise_for_upload_error(exc: Exception) -> None:
    if isinstance(exc, UnsupportedFileTypeError):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "File must be a valid PDF."
        ) from exc
    if isinstance(exc, UploadTooLargeError):
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "Upload exceeds the configured size limit.",
        ) from exc
    if isinstance(exc, PageLimitExceededError):
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "Document exceeds the configured page limit.",
        ) from exc
    if isinstance(exc, EncryptedDocumentError):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Encrypted or password-protected PDFs are not supported.",
        ) from exc
    if isinstance(exc, MalformedDocumentError):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "The file could not be parsed as a PDF.",
        ) from exc
    raise exc


@router.post("/parse", response_model=ParseDocumentResponse)
async def parse_document(
    file: UploadFile = File(...),  # noqa: B008
    settings: UploadSettings = Depends(load_upload_settings),  # noqa: B008
) -> ParseDocumentResponse:
    try:
        filename, _data, parsed = await read_and_parse_pdf(file, settings)
    except (
        UnsupportedFileTypeError,
        UploadTooLargeError,
        PageLimitExceededError,
        EncryptedDocumentError,
        MalformedDocumentError,
    ) as exc:
        _raise_for_upload_error(exc)
        raise  # unreachable; satisfies type checkers
    finally:
        await file.close()

    return ParseDocumentResponse(
        filename=filename,
        status=parsed.status,
        page_count=parsed.page_count,
        pages=[
            DocumentPageResponse(page_number=page.page_number, text=page.text)
            for page in parsed.pages
        ],
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document_route(
    file: UploadFile = File(...),  # noqa: B008
    settings: UploadSettings = Depends(load_upload_settings),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> DocumentResponse:
    try:
        document = await create_document(file, settings, session)
    except (
        UnsupportedFileTypeError,
        UploadTooLargeError,
        PageLimitExceededError,
        EncryptedDocumentError,
        MalformedDocumentError,
    ) as exc:
        _raise_for_upload_error(exc)
        raise  # unreachable; satisfies type checkers
    finally:
        await file.close()

    return DocumentResponse.model_validate(document)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document_route(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> DocumentResponse:
    try:
        document = await get_document(document_id, session)
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.") from exc

    return DocumentResponse.model_validate(document)
