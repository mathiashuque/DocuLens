"""Document upload and parsing HTTP route."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import UploadSettings, load_upload_settings
from app.schemas.document import DocumentPageResponse, ParseDocumentResponse
from app.services.document_parsing import (
    UnsupportedFileTypeError,
    UploadTooLargeError,
    read_and_parse_pdf,
)
from ingestion.errors import (
    EncryptedDocumentError,
    MalformedDocumentError,
    PageLimitExceededError,
)

router = APIRouter(prefix="/api/documents")


@router.post("/parse", response_model=ParseDocumentResponse)
async def parse_document(
    file: UploadFile = File(...),  # noqa: B008
    settings: UploadSettings = Depends(load_upload_settings),  # noqa: B008
) -> ParseDocumentResponse:
    try:
        filename, parsed = await read_and_parse_pdf(file, settings)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "File must be a valid PDF."
        ) from exc
    except UploadTooLargeError as exc:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "Upload exceeds the configured size limit.",
        ) from exc
    except PageLimitExceededError as exc:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "Document exceeds the configured page limit.",
        ) from exc
    except EncryptedDocumentError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Encrypted or password-protected PDFs are not supported.",
        ) from exc
    except MalformedDocumentError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "The file could not be parsed as a PDF.",
        ) from exc
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
