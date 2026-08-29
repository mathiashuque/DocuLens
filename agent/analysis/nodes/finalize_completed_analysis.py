"""Assembles the final result and assigns application-owned IDs.

Pure and I/O-free by design ("persist_completed_analysis" in the workflow
diagram): the actual database write happens in the API service after the
graph returns, keeping SQLAlchemy sessions out of graph/domain code.
"""

from typing import Any

from agent.analysis.result import assign_ids
from agent.analysis.state import AnalysisState


def finalize_completed_analysis(state: AnalysisState) -> dict[str, Any]:
    metadata = state.get("provider_metadata")
    summary = state.get("summary")
    if metadata is None or summary is None:
        return {
            "status": "failed",
            "failure_reason": "Analysis completed without a usable provider result.",
        }
    result = assign_ids(
        summary=summary,
        findings=state.get("valid_findings", []),
        dates=state.get("valid_dates", []),
        risks=state.get("valid_risks", []),
        metadata=metadata,
        retry_count=state.get("retry_count", 0),
    )
    return {"status": "completed", "result": result}
