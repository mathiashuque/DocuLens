"""Asserts the resolved classification is present in state.

Obtaining classification (reusing an existing completed result, or invoking
the classification service) is I/O and happens at the API service boundary
*before* this graph runs — the service calls the established classification
service, then seeds `document_type`/`classification_confidence` into the
graph's initial state. This node keeps the concern visible as a named,
directly testable graph step without pulling a database session into graph
code.
"""

from typing import Any

from agent.analysis.state import AnalysisState


def ensure_classification(state: AnalysisState) -> dict[str, Any]:
    if state.get("status") == "failed":
        return {}
    if not state.get("document_type"):
        return {
            "status": "failed",
            "failure_reason": "Classification is required before analysis.",
        }
    return {}


def route_by_document_type(state: AnalysisState) -> str:
    """Only a validated `contract` or `technical_specification`
    classification takes its specialized route.

    Routing depends solely on the persisted/validated `document_type`
    already in state, never filename or content heuristics.
    """
    if state.get("status") == "failed":
        return "fail"
    document_type = state.get("document_type")
    if document_type == "contract":
        return "contract"
    if document_type == "technical_specification":
        return "technical_specification"
    return "generic"
