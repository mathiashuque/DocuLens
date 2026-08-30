"""Extractor identity and bounded vocabularies for this slice.

All supported classifications intentionally route to the generic extractor
until a genuinely different specialized extractor exists (see the prompt's
"Meaningful LangGraph workflow" section). `GENERIC_EXTRACTOR` is what the API
and persistence layers record as `extractor`.
"""

from typing import Final, Literal, get_args

GENERIC_EXTRACTOR: Final[str] = "generic"

Importance = Literal["low", "medium", "high", "critical"]
ALLOWED_IMPORTANCE: Final[tuple[Importance, ...]] = get_args(Importance)

Severity = Literal["low", "medium", "high", "critical"]
ALLOWED_SEVERITY: Final[tuple[Severity, ...]] = get_args(Severity)
