"""Query boundary for the `document_classifications` table.

Only completed, evidence-validated classifications are ever inserted here;
the unique `document_id` constraint is what makes "latest completed" a
direct single-row lookup and POST idempotent.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import DocumentClassification


class ClassificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest_completed(
        self, document_id: uuid.UUID
    ) -> DocumentClassification | None:
        statement = select(DocumentClassification).where(
            DocumentClassification.document_id == document_id
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        document_id: uuid.UUID,
        document_type: str,
        confidence: float,
        reason: str,
        evidence: list[dict[str, object]],
        provider: str,
        model: str,
        latency_ms: int | None,
        input_tokens: int | None,
        output_tokens: int | None,
    ) -> DocumentClassification:
        classification = DocumentClassification(
            id=uuid.uuid4(),
            document_id=document_id,
            document_type=document_type,
            confidence=confidence,
            reason=reason,
            evidence=evidence,
            provider=provider,
            model=model,
            status="completed",
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        self._session.add(classification)
        await self._session.flush()
        await self._session.refresh(classification, attribute_names=["created_at"])
        return classification
