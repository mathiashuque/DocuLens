"""The one bounded targeted repair attempt.

Sends only the invalid items' descriptions/errors plus the same bounded
context (the minimum source evidence needed to repair them); valid items
already accumulated in state are never re-requested. A provider failure
during repair fails the run safely rather than looping further.
"""

from typing import Any

from agent.analysis.extraction import call_with_transport_retry
from agent.analysis.prompt import REPAIR_SYSTEM_INSTRUCTION, render_repair_content
from agent.analysis.provider import ProviderRequestError
from agent.analysis.state import AnalysisState


async def retry_invalid_subset(state: AnalysisState) -> dict[str, Any]:
    context = state["context"]
    provider = state["provider"]
    invalid_items = state.get("invalid_items", [])
    retry_count = state.get("retry_count", 0) + 1
    descriptions = [
        f"{item['kind']}: {item['description']} — {item['error']}"
        for item in invalid_items
    ]
    user_content = render_repair_content(context, descriptions)

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

    return {
        "pending_findings": repaired.findings,
        "pending_dates": repaired.important_dates,
        "pending_risks": repaired.risks,
        "retry_count": retry_count,
        "provider_metadata": metadata,
    }
