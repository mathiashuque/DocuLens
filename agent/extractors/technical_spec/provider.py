"""Provider-agnostic structured-generation boundary for technical-
specification extraction.

Reuses classification's error types and metadata shape directly (they are
not classification-specific in content) instead of redefining them here,
exactly as `agent.analysis.provider` and `agent.extractors.contract.provider`
do.
"""

from typing import Protocol

from agent.classification.provider import (
    ProviderMetadata,
    ProviderRequestError,
    ProviderUnavailableError,
)
from agent.extractors.technical_spec.types import (
    TechnicalSpecExtractionCandidate,
    TechnicalSpecRepairCandidate,
)

__all__ = [
    "ProviderMetadata",
    "ProviderRequestError",
    "ProviderUnavailableError",
    "StructuredTechnicalSpecProvider",
]


class StructuredTechnicalSpecProvider(Protocol):
    """Two structured-generation operations: full extraction and repair."""

    async def extract(
        self, *, system_instruction: str, user_content: str
    ) -> tuple[TechnicalSpecExtractionCandidate, ProviderMetadata]:
        """Full first-pass technical-specification extraction."""
        ...

    async def repair(
        self, *, system_instruction: str, user_content: str
    ) -> tuple[TechnicalSpecRepairCandidate, ProviderMetadata]:
        """Targeted repair of only the invalid items from a prior pass."""
        ...
