"""Runs the technical-specification route's first-pass structured
extraction call.

Only reached when `document_type == "technical_specification"` (see
`route_by_document_type` in `agent.analysis.graph`); contract and generic
documents never invoke this node and therefore never call the
technical-specification provider.
"""

from typing import Any

from agent.analysis.extraction import call_with_transport_retry
from agent.analysis.state import AnalysisState
from agent.extractors.technical_spec.context import (
    DEFAULT_TECHNICAL_SPEC_BUDGET_CHARS,
    select_technical_spec_context,
)
from agent.extractors.technical_spec.prompt import (
    SYSTEM_INSTRUCTION,
    render_user_content,
)
from agent.extractors.technical_spec.validation import resolve_category_precedence


async def extract_technical_spec_requirements(state: AnalysisState) -> dict[str, Any]:
    if state.get("status") == "failed":
        return {}

    context = select_technical_spec_context(
        filename=state["filename"],
        pages=state["pages"],
        section_titles=state.get("section_titles", []),
        sections=state.get("sections", []),
        budget_chars=state.get("budget_chars", DEFAULT_TECHNICAL_SPEC_BUDGET_CHARS),
    )
    provider = state["technical_spec_provider"]
    user_content = render_user_content(context)

    candidate, metadata = await call_with_transport_retry(
        provider.extract,
        system_instruction=SYSTEM_INSTRUCTION,
        user_content=user_content,
    )

    return {
        "technical_spec_context": context,
        "pending_requirements": resolve_category_precedence(candidate.requirements),
        "pending_constraints": candidate.constraints,
        "pending_dependencies": candidate.dependencies,
        "valid_requirements": [],
        "valid_constraints": [],
        "valid_dependencies": [],
        "technical_spec_metadata": metadata,
    }
