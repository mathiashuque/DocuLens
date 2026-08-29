"""Assembles the final result and assigns application-owned IDs.

Pure and I/O-free by design ("persist_completed_analysis" in the workflow
diagram): the actual database write happens in the API service after the
graph returns, keeping SQLAlchemy sessions out of graph/domain code.

For a `contract` or `technical_specification` document, this also assembles
the matching specialized result (from the same validated, retried item
sets) and attaches it to the generic result's `specialized` field. A
document whose common generic analysis succeeded but whose specialized
items never became usable (no specialized metadata reached this node — e.g.
the specialized provider was never called because no invalid specialized
items forced a repair) still persists with a valid, possibly-empty
specialized result.
"""

from typing import Any

from agent.analysis.result import SpecializedAnalysisResult, assign_ids
from agent.analysis.state import AnalysisState
from agent.extractors.contract.result import assign_contract_ids
from agent.extractors.technical_spec.result import assign_technical_spec_ids


def finalize_completed_analysis(state: AnalysisState) -> dict[str, Any]:
    metadata = state.get("provider_metadata")
    summary = state.get("summary")
    if metadata is None or summary is None:
        return {
            "status": "failed",
            "failure_reason": "Analysis completed without a usable provider result.",
        }

    document_type = state.get("document_type")
    specialized: SpecializedAnalysisResult | None = None
    if document_type == "contract":
        contract_metadata = state.get("contract_metadata")
        if contract_metadata is None:
            return {
                "status": "failed",
                "failure_reason": (
                    "Contract analysis completed without a usable contract "
                    "provider result."
                ),
            }
        specialized = assign_contract_ids(
            parties=state.get("valid_parties", []),
            obligations=state.get("valid_obligations", []),
            payment_terms=state.get("valid_payment_terms", []),
            clauses=state.get("valid_clauses", []),
            metadata=contract_metadata,
        )
    elif document_type == "technical_specification":
        technical_spec_metadata = state.get("technical_spec_metadata")
        if technical_spec_metadata is None:
            return {
                "status": "failed",
                "failure_reason": (
                    "Technical spec analysis completed without a usable "
                    "technical spec provider result."
                ),
            }
        specialized = assign_technical_spec_ids(
            requirements=state.get("valid_requirements", []),
            constraints=state.get("valid_constraints", []),
            dependencies=state.get("valid_dependencies", []),
            metadata=technical_spec_metadata,
        )

    result = assign_ids(
        summary=summary,
        findings=state.get("valid_findings", []),
        dates=state.get("valid_dates", []),
        risks=state.get("valid_risks", []),
        metadata=metadata,
        retry_count=state.get("retry_count", 0),
        specialized=specialized,
    )
    return {"status": "completed", "result": result}
