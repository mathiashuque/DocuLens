"""Terminal failure node: never persist unsupported claims."""

from typing import Any

from agent.analysis.state import AnalysisState


def fail_safely(state: AnalysisState) -> dict[str, Any]:
    reason = (
        state.get("failure_reason")
        or "Analysis produced unsupported or invalid claims after the retry."
    )
    return {"status": "failed", "failure_reason": reason, "result": None}
