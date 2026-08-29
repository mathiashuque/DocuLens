"""Builds the deterministic, bounded extraction context from state's pages.

Reuses `select_classification_context` directly — the same page-labeled,
budget-enforced, order-stable excerpt selection classification uses, just
with a larger default budget suited to multi-field extraction.
"""

from typing import Any

from agent.analysis.state import AnalysisState
from agent.classification.context import (
    DEFAULT_BUDGET_CHARS,
    select_classification_context,
)

DEFAULT_ANALYSIS_BUDGET_CHARS = DEFAULT_BUDGET_CHARS * 2


def build_extraction_context(state: AnalysisState) -> dict[str, Any]:
    if state.get("status") == "failed":
        return {}
    context = select_classification_context(
        filename=state["filename"],
        pages=state["pages"],
        section_titles=state.get("section_titles", []),
        budget_chars=state.get("budget_chars", DEFAULT_ANALYSIS_BUDGET_CHARS),
    )
    return {"context": context}
