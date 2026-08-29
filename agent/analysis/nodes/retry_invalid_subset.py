"""The one bounded targeted repair attempt.

Sends only the invalid items' descriptions/errors plus the same bounded
context (the minimum source evidence needed to repair them); valid items
already accumulated in state are never re-requested. A provider failure
during repair fails the run safely rather than looping further.

Invalid items are split by kind: generic (finding/date/risk) items are
repaired via the generic provider using the generic context, and contract
(party/obligation/payment_term/clause) items are repaired via the contract
provider using the contract context — each called only when that kind
actually has invalid items, so a contract-only failure never triggers a
generic provider call and vice versa. Both repairs still count as a single
retry against the graph's shared, strict retry budget.
"""

from typing import Any

from agent.analysis.extraction import call_with_transport_retry
from agent.analysis.prompt import REPAIR_SYSTEM_INSTRUCTION, render_repair_content
from agent.analysis.provider import ProviderRequestError
from agent.analysis.state import AnalysisState, InvalidItem
from agent.extractors.contract.prompt import (
    REPAIR_SYSTEM_INSTRUCTION as CONTRACT_REPAIR_SYSTEM_INSTRUCTION,
)
from agent.extractors.contract.prompt import (
    render_repair_content as render_contract_repair_content,
)

_GENERIC_KINDS = {"finding", "date", "risk"}


def _describe(item: InvalidItem) -> str:
    return f"{item['kind']}: {item['description']} — {item['error']}"


async def retry_invalid_subset(state: AnalysisState) -> dict[str, Any]:
    invalid_items = state.get("invalid_items", [])
    retry_count = state.get("retry_count", 0) + 1
    generic_invalid = [item for item in invalid_items if item["kind"] in _GENERIC_KINDS]
    contract_invalid = [
        item for item in invalid_items if item["kind"] not in _GENERIC_KINDS
    ]

    updates: dict[str, Any] = {
        "pending_findings": [],
        "pending_dates": [],
        "pending_risks": [],
        "pending_parties": [],
        "pending_obligations": [],
        "pending_payment_terms": [],
        "pending_clauses": [],
        "retry_count": retry_count,
    }

    if generic_invalid:
        context = state["context"]
        provider = state["provider"]
        user_content = render_repair_content(
            context, [_describe(item) for item in generic_invalid]
        )
        try:
            repaired, metadata = await call_with_transport_retry(
                provider.repair,
                system_instruction=REPAIR_SYSTEM_INSTRUCTION,
                user_content=user_content,
            )
        except ProviderRequestError:
            return {
                "status": "failed",
                "failure_reason": "Analysis provider failed during the repair retry.",
                "retry_count": retry_count,
            }
        updates["pending_findings"] = repaired.findings
        updates["pending_dates"] = repaired.important_dates
        updates["pending_risks"] = repaired.risks
        updates["provider_metadata"] = metadata

    if contract_invalid:
        contract_context = state["contract_context"]
        contract_provider = state["contract_provider"]
        contract_user_content = render_contract_repair_content(
            contract_context, [_describe(item) for item in contract_invalid]
        )
        try:
            contract_repaired, contract_metadata = await call_with_transport_retry(
                contract_provider.repair,
                system_instruction=CONTRACT_REPAIR_SYSTEM_INSTRUCTION,
                user_content=contract_user_content,
            )
        except ProviderRequestError:
            return {
                "status": "failed",
                "failure_reason": ("Contract provider failed during the repair retry."),
                "retry_count": retry_count,
            }
        updates["pending_parties"] = contract_repaired.parties
        updates["pending_obligations"] = contract_repaired.obligations
        updates["pending_payment_terms"] = contract_repaired.payment_terms
        updates["pending_clauses"] = contract_repaired.clauses
        updates["contract_metadata"] = contract_metadata

    return updates
