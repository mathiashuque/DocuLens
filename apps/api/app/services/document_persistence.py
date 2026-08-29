"""Upload -> parse -> hash -> persist orchestration and document retrieval.

Keeps HTTP status-code mapping out of this module: it raises typed errors
that the route maps to responses, mirroring `document_parsing`.
"""

import hashlib
import uuid

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import UploadSettings
from app.db.repository import DocumentRepository
from app.models.document import Document
from app.services.document_parsing import read_and_parse_pdf
from ingestion.sections import detect_sections


class DocumentNotFoundError(Exception):
    """No document exists for the given ID."""


async def create_document(
    upload: UploadFile, settings: UploadSettings, session: AsyncSession
) -> Document:
    filename, data, parsed = await read_and_parse_pdf(upload, settings)
    content_hash = hashlib.sha256(data).hexdigest()
    sections = detect_sections(parsed.pages)
    repository = DocumentRepository(session)
    return await repository.create(
        filename=filename,
        content_hash=content_hash,
        status=parsed.status,
        pages=parsed.pages,
        sections=sections,
    )


async def get_document(document_id: uuid.UUID, session: AsyncSession) -> Document:
    repository = DocumentRepository(session)
    document = await repository.get(document_id)
    if document is None:
        raise DocumentNotFoundError(str(document_id))
    return document
