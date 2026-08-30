"""Provider-agnostic structured-generation boundary for grounded QA.

Reuses classification's error types and metadata shape directly (they are
not classification-specific in content) instead of redefining them here.
"""

from typing import Protocol

from agent.classification.provider import (
    ProviderMetadata,
    ProviderRequestError,
    ProviderUnavailableError,
)
from agent.grounded_qa.types import GroundedAnswerCandidate

__all__ = [
    "GroundedQaProvider",
    "ProviderMetadata",
    "ProviderRequestError",
    "ProviderUnavailableError",
]


class GroundedQaProvider(Protocol):
    """Two structured-generation operations: first-pass answer and one
    targeted repair of a structurally usable but invalid candidate."""

    async def answer(
        self, *, system_instruction: str, user_content: str
    ) -> tuple[GroundedAnswerCandidate, ProviderMetadata]:
        """First-pass grounded answer. Same error contract as
        classification's `StructuredClassificationProvider.classify`."""
        ...

    async def repair(
        self, *, system_instruction: str, user_content: str
    ) -> tuple[GroundedAnswerCandidate, ProviderMetadata]:
        """Targeted repair of a prior candidate that failed citation
        validation."""
        ...
