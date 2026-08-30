"""Transport-level retry-once helper shared by the extract and repair nodes.

Distinct from the graph's content-level "retry invalid subset" loop: this
only retries a single provider call once when the provider itself reports a
retryable transport/malformed-output failure (timeout, empty parse, etc.),
mirroring classification's established per-call retry behavior.
"""

from collections.abc import Awaitable, Callable
from typing import TypeVar

from agent.analysis.provider import ProviderMetadata, ProviderRequestError

T = TypeVar("T")


async def call_with_transport_retry(
    call: Callable[..., Awaitable[tuple[T, ProviderMetadata]]],
    /,
    **kwargs: object,
) -> tuple[T, ProviderMetadata]:
    try:
        return await call(**kwargs)
    except ProviderRequestError as exc:
        if not exc.retryable:
            raise
        return await call(**kwargs)
