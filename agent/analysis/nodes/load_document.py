"""First graph node: defensive check that the state's pages carry usable
text. The actual `ocr_required`/textless eligibility gate runs in the API
service before the graph is invoked (mirroring classification's own gate);
this node exists so the diagrammed workflow step is a real, directly
testable node rather than an implicit assumption.
"""

from typing import Any

from agent.analysis.state import AnalysisState


def load_document(state: AnalysisState) -> dict[str, Any]:
    pages = state.get("pages") or []
    if not any(text.strip() for _, text in pages):
        return {
            "status": "failed",
            "failure_reason": "Document has no extracted text to analyze.",
        }
    return {"status": "pending"}
