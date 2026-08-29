"""Read-only allowance visibility for the current anonymous session."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.quota import UsageAllowanceResponse, UsageResponse
from app.services.quota import get_usage_allowances, require_anonymous_identity

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("", response_model=UsageResponse)
async def get_usage(
    document_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    quota_identity: str | None = Depends(require_anonymous_identity),
) -> UsageResponse:
    enforced, allowances = await get_usage_allowances(
        session, quota_identity, document_id=document_id
    )
    return UsageResponse(
        enforced=enforced,
        allowances=[
            UsageAllowanceResponse(
                category=item.category,
                limit=item.limit,
                remaining=item.remaining,
                retry_at=item.retry_at,
            )
            for item in allowances
        ],
    )
