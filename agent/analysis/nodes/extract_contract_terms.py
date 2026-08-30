"""Runs the contract route's first-pass structured extraction call.

Only reached when `document_type == "contract"` (see `route_by_document_type`
in `agent.analysis.graph`); generic and technical_specification documents
never invoke this node and therefore never call the contract provider.
"""

from typing import Any

from agent.analysis.extraction import call_with_transport_retry
from agent.analysis.state import AnalysisState
from agent.extractors.contract.context import (
    DEFAULT_CONTRACT_BUDGET_CHARS,
    select_contract_context,
)
from agent.extractors.contract.prompt import SYSTEM_INSTRUCTION, render_user_content


async def extract_contract_terms(state: AnalysisState) -> dict[str, Any]:
    if state.get("status") == "failed":
        return {}

    context = select_contract_context(
        filename=state["filename"],
        pages=state["pages"],
        section_titles=state.get("section_titles", []),
        sections=state.get("sections", []),
        budget_chars=state.get("budget_chars", DEFAULT_CONTRACT_BUDGET_CHARS),
    )
    provider = state["contract_provider"]
    user_content = render_user_content(context)

    candidate, metadata = await call_with_transport_retry(
        provider.extract,
        system_instruction=SYSTEM_INSTRUCTION,
        user_content=user_content,
    )

    return {
        "contract_context": context,
        "pending_parties": candidate.parties,
        "pending_obligations": candidate.obligations,
        "pending_payment_terms": candidate.payment_terms,
        "pending_clauses": candidate.clauses,
        "valid_parties": [],
        "valid_obligations": [],
        "valid_payment_terms": [],
        "valid_clauses": [],
        "contract_metadata": metadata,
    }
