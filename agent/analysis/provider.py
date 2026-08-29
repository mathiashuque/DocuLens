"""Provider-agnostic structured-generation boundary for generic analysis.

Reuses classification's error types and metadata shape directly (they are
not classification-specific in content) instead of redefining them here.
"""

from typing import Protocol

from agent.analysis.types import GenericAnalysisCandidate, RepairCandidate
from agent.classification.provider import (
    ProviderMetadata,
    ProviderRequestError,
    ProviderUnavailableError,
)

__all__ = [
    "ProviderMetadata",
    "ProviderRequestError",
    "ProviderUnavailableError",
    "StructuredAnalysisProvider",
]


class StructuredAnalysisProvider(Protocol):
    """Two structured-generation operations: full extraction and repair."""

    async def extract(
        self, *, system_instruction: str, user_content: str
    ) -> tuple[GenericAnalysisCandidate, ProviderMetadata]:
        """Full first-pass extraction. Same error contract as classification's
        `StructuredClassificationProvider.classify`."""
        ...

    async def repair(
        self, *, system_instruction: str, user_content: str
    ) -> tuple[RepairCandidate, ProviderMetadata]:
        """Targeted repair of only the invalid items from a prior pass."""
        ...
