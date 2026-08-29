"""Deterministic, bounded context selection for classification.

Classification must not read the whole document. This module builds a small,
reproducible excerpt set from already-persisted data: filename, the start of
the document, a handful of representative page samples spread through longer
documents, and detected section titles. Every excerpt keeps its physical page
number. Selection is pure and order-stable so the same document always
produces the same context.
"""

from pydantic import BaseModel, Field

DEFAULT_BUDGET_CHARS = 6000
MAX_PAGE_SAMPLES = 5
MAX_SECTION_TITLES = 15
MIN_PAGE_CHARS = 200


class PageExcerpt(BaseModel):
    page: int = Field(gt=0)
    text: str


class ClassificationContext(BaseModel):
    """Bounded, page-labeled input ready for prompt rendering."""

    filename: str
    excerpts: list[PageExcerpt]
    section_titles: list[str]
    budget_chars: int
    truncated: bool

    @property
    def total_excerpt_chars(self) -> int:
        return sum(len(excerpt.text) for excerpt in self.excerpts)


def _sample_indices(count: int, num_samples: int) -> list[int]:
    """Evenly spaced, stable indices into a sequence of length `count`."""
    if count <= num_samples:
        return list(range(count))
    step = count / num_samples
    return sorted({int(index * step) for index in range(num_samples)})


def select_classification_context(
    *,
    filename: str,
    pages: list[tuple[int, str]],
    section_titles: list[str] | None = None,
    budget_chars: int = DEFAULT_BUDGET_CHARS,
) -> ClassificationContext:
    """Build a deterministic, bounded classification context.

    `pages` is `(page_number, text)` in ascending page order. Blank pages
    (empty after stripping) contribute no excerpt. The first non-blank page
    is always included (the document's beginning); additional pages are
    sampled at stable, evenly spaced positions through the remaining
    non-blank pages until the budget is spent.
    """
    non_blank = [(number, text) for number, text in pages if text.strip()]
    titles = list(dict.fromkeys(section_titles or []))[:MAX_SECTION_TITLES]

    if not non_blank:
        return ClassificationContext(
            filename=filename,
            excerpts=[],
            section_titles=titles,
            budget_chars=budget_chars,
            truncated=False,
        )

    beginning_number, beginning_text = non_blank[0]
    remaining = non_blank[1:]
    sample_indices = _sample_indices(len(remaining), MAX_PAGE_SAMPLES - 1)

    selected = [(beginning_number, beginning_text)] + [
        remaining[index] for index in sample_indices
    ]
    selected.sort(key=lambda item: item[0])

    per_page_cap = max(MIN_PAGE_CHARS, budget_chars // max(len(selected), 1))

    excerpts: list[PageExcerpt] = []
    used_chars = 0
    truncated = False
    for page_number, text in selected:
        remaining_budget = budget_chars - used_chars
        if remaining_budget <= 0:
            truncated = True
            break
        cap = min(per_page_cap, remaining_budget)
        page_text = text[:cap]
        if len(page_text) < len(text):
            truncated = True
        excerpts.append(PageExcerpt(page=page_number, text=page_text))
        used_chars += len(page_text)

    return ClassificationContext(
        filename=filename,
        excerpts=excerpts,
        section_titles=titles,
        budget_chars=budget_chars,
        truncated=truncated,
    )
