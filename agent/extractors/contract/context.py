"""Deterministic, bounded context selection for contract extraction.

Thin wrapper over `agent.classification.context.select_keyword_priority_context`
(the shared keyword-priority-then-sampling strategy specialized extractors
use) with contract-specific priority keywords: payment, fee, term, renewal,
termination, liability, confidentiality, obligations, parties.
"""

from agent.classification.context import (
    DEFAULT_BUDGET_CHARS,
    ClassificationContext,
    SectionSpan,
    select_keyword_priority_context,
)

__all__ = [
    "DEFAULT_CONTRACT_BUDGET_CHARS",
    "SectionSpan",
    "select_contract_context",
]

DEFAULT_CONTRACT_BUDGET_CHARS = DEFAULT_BUDGET_CHARS * 2

_PRIORITY_KEYWORDS: tuple[str, ...] = (
    "payment",
    "fee",
    "term",
    "renewal",
    "termination",
    "liability",
    "confidential",
    "obligation",
    "parties",
)


def select_contract_context(
    *,
    filename: str,
    pages: list[tuple[int, str]],
    section_titles: list[str] | None = None,
    sections: list[SectionSpan] | None = None,
    budget_chars: int = DEFAULT_CONTRACT_BUDGET_CHARS,
) -> ClassificationContext:
    return select_keyword_priority_context(
        filename=filename,
        pages=pages,
        priority_keywords=_PRIORITY_KEYWORDS,
        section_titles=section_titles,
        sections=sections,
        budget_chars=budget_chars,
    )
