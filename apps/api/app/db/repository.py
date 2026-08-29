"""Query boundary for the `documents` / `document_pages` aggregate.

Kept to the two operations this slice needs; not a generic base repository.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentPage, DocumentSection
from ingestion.models import DocumentPage as ParsedPage
from ingestion.sections import SectionCandidate


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
        sections: list[SectionCandidate] | None = None,
    ) -> Document:
        """Insert a document, its parsed pages, and detected sections as one flush.

        Section IDs are generated up front so parent relationships can be
        mapped explicitly by candidate position rather than inferred from
        row order. A constraint violation on any row raises and leaves
        nothing committed; the caller's transaction boundary owns the
        rollback.
        """
        section_candidates = sections or []
        section_ids = [uuid.uuid4() for _ in section_candidates]
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
            sections=[
                DocumentSection(
                    id=section_ids[index],
                    parent_section_id=(
                        section_ids[candidate.parent_index]
                        if candidate.parent_index is not None
                        else None
                    ),
                    ordinal=index + 1,
                    title=candidate.title,
                    level=candidate.level,
                    page_start=candidate.page_start,
                    page_end=candidate.page_end,
                    section_path=candidate.section_path,
                    text=candidate.text,
                )
                for index, candidate in enumerate(section_candidates)
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
            .options(selectinload(Document.pages), selectinload(Document.sections))
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
