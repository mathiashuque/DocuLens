"""Query boundary for the `documents` / `document_pages` aggregate.

Kept to the two operations this slice needs; not a generic base repository.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentPage
from ingestion.models import DocumentPage as ParsedPage


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        filename: str,
        content_hash: str,
        status: str,
        pages: list[ParsedPage],
    ) -> Document:
        """Insert a document and every parsed page as one flush.

        A constraint violation on any page raises and leaves nothing
        committed; the caller's transaction boundary owns the rollback.
        """
        document = Document(
            id=uuid.uuid4(),
            filename=filename,
            content_hash=content_hash,
            page_count=len(pages),
            status=status,
            pages=[
                DocumentPage(page_number=page.page_number, text=page.text)
                for page in pages
            ],
        )
        self._session.add(document)
        await self._session.flush()
        await self._session.refresh(document, attribute_names=["created_at"])
        return document

    async def get(self, document_id: uuid.UUID) -> Document | None:
        statement = (
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.pages))
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
