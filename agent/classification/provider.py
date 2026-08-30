"""Provider-agnostic structured-generation boundary.

Routes, validation, and persistence code depend only on this module. Provider
SDK imports and payload details stay inside concrete adapters
(`agent/classification/providers/`).
"""

from dataclasses import dataclass
from typing import Protocol

from agent.classification.types import ClassificationCandidate


class ProviderUnavailableError(Exception):
    """The configured provider is missing, misconfigured, or unreachable.

    Maps to a safe HTTP 503 at the API boundary. Never carries key material,
    headers, or endpoint details in its message.
    """


class ProviderRequestError(Exception):
    """A provider call failed after allowed retries (timeout, malformed
    structured output, quota/policy rejection, transport error).

    Maps to a safe HTTP 502 at the API boundary.
    """

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class ProviderMetadata:
    """Safe, non-sensitive metadata about one completed provider call."""

    provider: str
    model: str
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


class StructuredClassificationProvider(Protocol):
    """One structured-generation operation: prompt in, typed candidate out."""

    async def classify(
        self, *, system_instruction: str, user_content: str
    ) -> tuple[ClassificationCandidate, ProviderMetadata]:
        """Return a structured candidate plus safe call metadata.

        Raises `ProviderUnavailableError` for configuration problems and
        `ProviderRequestError` for exhausted/transport/malformed-output
        failures. Never raises on low confidence; that is a downstream
        thresholding decision, not a provider failure.
        """
        ...
