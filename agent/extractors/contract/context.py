"""Deterministic, bounded context selection for contract extraction.

Reuses classification's `ClassificationContext`/`PageExcerpt` shape (and
therefore its prompt rendering) rather than inventing a parallel one.
Contract context prioritizes, in stable order: the title/introductory page,
pages whose detected section titles match contract-relevant keywords
(payment, term, renewal, termination, liability, confidentiality,
obligations), then the same evenly spaced representative sampling
classification/generic analysis use for any remaining budget. Section-title
matching is best-effort and never assumed present: when no sections are
supplied (or none match), selection falls back to the plain page-sampling
strategy untouched.
"""

from dataclasses import dataclass

from agent.classification.context import (
    DEFAULT_BUDGET_CHARS,
    MIN_PAGE_CHARS,
    ClassificationContext,
    PageExcerpt,
    select_classification_context,
)

DEFAULT_CONTRACT_BUDGET_CHARS = DEFAULT_BUDGET_CHARS * 2


def _sample_indices(count: int, num_samples: int) -> list[int]:
    """Evenly spaced, stable indices into a sequence of length `count`."""
    if num_samples <= 0 or count <= 0:
        return []
    if count <= num_samples:
        return list(range(count))
    step = count / num_samples
    return sorted({int(index * step) for index in range(num_samples)})


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


@dataclass(frozen=True)
class SectionSpan:
    """A detected section's title and inclusive physical page range."""

    title: str
    page_start: int
    page_end: int


def _matches_priority_keyword(title: str) -> bool:
    lowered = title.lower()
    return any(keyword in lowered for keyword in _PRIORITY_KEYWORDS)


def _priority_pages(sections: list[SectionSpan]) -> list[int]:
    """Physical pages covered by contract-relevant sections, in the stable
    order the sections were supplied (their persisted ordinal order)."""
    pages: list[int] = []
    seen: set[int] = set()
    for section in sections:
        if not _matches_priority_keyword(section.title):
            continue
        for page in range(section.page_start, section.page_end + 1):
            if page not in seen:
                seen.add(page)
                pages.append(page)
    return pages


def select_contract_context(
    *,
    filename: str,
    pages: list[tuple[int, str]],
    section_titles: list[str] | None = None,
    sections: list[SectionSpan] | None = None,
    budget_chars: int = DEFAULT_CONTRACT_BUDGET_CHARS,
) -> ClassificationContext:
    non_blank = [(number, text) for number, text in pages if text.strip()]
    if not non_blank:
        return select_classification_context(
            filename=filename,
            pages=pages,
            section_titles=section_titles,
            budget_chars=budget_chars,
        )

    page_text_by_number = dict(non_blank)
    beginning_number, _ = non_blank[0]

    priority_numbers = [
        number
        for number in _priority_pages(sections or [])
        if number in page_text_by_number and number != beginning_number
    ]

    if not priority_numbers:
        # No matching section structure: fall back to plain sampling exactly
        # as classification/generic analysis do.
        return select_classification_context(
            filename=filename,
            pages=pages,
            section_titles=section_titles,
            budget_chars=budget_chars,
        )

    selected_numbers = [beginning_number, *priority_numbers]

    remaining_candidates = [
        number for number, _ in non_blank if number not in set(selected_numbers)
    ]
    remaining_budget_slots = max(0, 5 - len(selected_numbers))
    if remaining_candidates and remaining_budget_slots:
        sample_positions = _sample_indices(
            len(remaining_candidates), remaining_budget_slots
        )
        selected_numbers.extend(remaining_candidates[pos] for pos in sample_positions)

    selected_numbers = sorted(dict.fromkeys(selected_numbers))
    per_page_cap = max(MIN_PAGE_CHARS, budget_chars // max(len(selected_numbers), 1))

    excerpts: list[PageExcerpt] = []
    used_chars = 0
    truncated = False
    for number in selected_numbers:
        text = page_text_by_number[number]
        remaining_budget = budget_chars - used_chars
        if remaining_budget <= 0:
            truncated = True
            break
        cap = min(per_page_cap, remaining_budget)
        page_text = text[:cap]
        if len(page_text) < len(text):
            truncated = True
        excerpts.append(PageExcerpt(page=number, text=page_text))
        used_chars += len(page_text)

    titles = list(dict.fromkeys(section_titles or []))[:15]
    return ClassificationContext(
        filename=filename,
        excerpts=excerpts,
        section_titles=titles,
        budget_chars=budget_chars,
        truncated=truncated,
    )
