"""Provider-agnostic structured-generation boundary for contract extraction.

Reuses classification's error types and metadata shape directly (they are
not classification-specific in content) instead of redefining them here,
exactly as `agent.analysis.provider` does.
"""

from typing import Protocol

from agent.classification.provider import (
    ProviderMetadata,
    ProviderRequestError,
    ProviderUnavailableError,
)
from agent.extractors.contract.types import (
    ContractExtractionCandidate,
    ContractRepairCandidate,
)

__all__ = [
    "ProviderMetadata",
    "ProviderRequestError",
    "ProviderUnavailableError",
    "StructuredContractProvider",
]


class StructuredContractProvider(Protocol):
    """Two structured-generation operations: full extraction and repair."""

    async def extract(
        self, *, system_instruction: str, user_content: str
    ) -> tuple[ContractExtractionCandidate, ProviderMetadata]:
        """Full first-pass contract extraction."""
        ...

    async def repair(
        self, *, system_instruction: str, user_content: str
    ) -> tuple[ContractRepairCandidate, ProviderMetadata]:
        """Targeted repair of only the invalid items from a prior pass."""
        ...
