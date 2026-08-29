"""Read-only public contracts for explicitly marked precomputed demos."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import DocumentRepository
from app.db.session import get_session
from app.schemas.document import DemoCardResponse, DocumentResponse

router = APIRouter(prefix="/api/demos")


@router.get("", response_model=list[DemoCardResponse])
async def list_demos(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[DemoCardResponse]:
    documents = await DocumentRepository(session).list_demos()
    return [
        DemoCardResponse(
            slug=document.demo_slug or "",
            title=document.demo_title or "",
            description=document.demo_description or "",
            document_type=document.demo_document_type,  # type: ignore[arg-type]
            page_count=document.page_count,
            document_id=document.id,
        )
        for document in documents
    ]


@router.get("/{slug}", response_model=DocumentResponse)
async def get_demo(
    slug: str,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> DocumentResponse:
    document = await DocumentRepository(session).get_demo_by_slug(slug)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Demo not found.")
    return DocumentResponse.model_validate(document)
