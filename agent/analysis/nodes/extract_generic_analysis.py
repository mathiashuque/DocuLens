"""Runs the first-pass structured extraction call.

Provider errors (`ProviderUnavailableError`, an exhausted/non-retryable
`ProviderRequestError`) propagate out of this node to the graph caller,
which maps them the same way classification does (503/502) — they are not
represented as graph state/conditional edges, since they are not part of
the "meaningful validation/retry" branching the workflow diagrams.
"""

from typing import Any

from agent.analysis.extraction import call_with_transport_retry
from agent.analysis.prompt import SYSTEM_INSTRUCTION, render_user_content
from agent.analysis.state import AnalysisState


async def extract_generic_analysis(state: AnalysisState) -> dict[str, Any]:
    if state.get("status") == "failed":
        return {}
    context = state["context"]
    provider = state["provider"]
    user_content = render_user_content(context)

    candidate, metadata = await call_with_transport_retry(
        provider.extract,
        system_instruction=SYSTEM_INSTRUCTION,
        user_content=user_content,
    )

    return {
        "summary": candidate.summary,
        "pending_findings": candidate.findings,
        "pending_dates": candidate.important_dates,
        "pending_risks": candidate.risks,
        "valid_findings": [],
        "valid_dates": [],
        "valid_risks": [],
        "retry_count": 0,
        "provider_metadata": metadata,
    }
