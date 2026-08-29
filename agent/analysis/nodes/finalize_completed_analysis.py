"""Assembles the final result and assigns application-owned IDs.

Pure and I/O-free by design ("persist_completed_analysis" in the workflow
diagram): the actual database write happens in the API service after the
graph returns, keeping SQLAlchemy sessions out of graph/domain code.

For a `contract` document, this also assembles the specialized
`ContractAnalysisResult` (from the same validated, retried item sets) and
attaches it to the generic result's `specialized` field. A contract whose
common generic analysis succeeded but whose contract items never became
usable (no contract_metadata reached this node — e.g. the contract provider
was never called because no invalid contract items forced a repair) still
persists with a valid, possibly-empty specialized result.
"""

from typing import Any

from agent.analysis.result import assign_ids
from agent.analysis.state import AnalysisState
from agent.extractors.contract.result import assign_contract_ids


def finalize_completed_analysis(state: AnalysisState) -> dict[str, Any]:
    metadata = state.get("provider_metadata")
    summary = state.get("summary")
    if metadata is None or summary is None:
        return {
            "status": "failed",
            "failure_reason": "Analysis completed without a usable provider result.",
        }

    specialized = None
    if state.get("document_type") == "contract":
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
