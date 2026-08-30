"""The generic analysis LangGraph: typed state, small directly testable
nodes, and conditional edges for validation/retry — not a sequential wrapper.

```text
load_document -> ensure_classification -> route_by_document_type
    --contract----------------> extract_contract_terms ------------+
    --technical_specification-> extract_technical_spec_requirements+
    --generic------------------------------------------------------+
                                                                     v
                                                    build_extraction_context
                                                                     |
                                                                     v
                                extract_generic_analysis -> validate_analysis
        --valid--------------------------> finalize_completed_analysis -> END
        --invalid, retry_count == 0------> retry_invalid_subset -> validate_analysis
        --invalid, retry_count == 1------> fail_safely -> END
```

`load_document`/`ensure_classification` can themselves fail (no usable text,
no classification); either short-circuits straight to `fail_safely`. Only a
validated `contract` classification reaches `extract_contract_terms`, and
only a validated `technical_specification` classification reaches
`extract_technical_spec_requirements` — the graph's only nodes that can call
their respective specialized providers, and mutually exclusive since a
document has exactly one validated classification. Common generic analysis
still runs afterward for both, and `validate_analysis`/
`retry_invalid_subset` validate and (within the same bounded retry) repair
the generic candidate set together with whichever specialized candidate set
(contract or technical-spec) is present.
"""

from langgraph.graph import END, StateGraph

from agent.analysis.nodes.build_extraction_context import build_extraction_context
from agent.analysis.nodes.ensure_classification import (
    ensure_classification,
    route_by_document_type,
)
from agent.analysis.nodes.extract_contract_terms import extract_contract_terms
from agent.analysis.nodes.extract_generic_analysis import extract_generic_analysis
from agent.analysis.nodes.extract_technical_spec_requirements import (
    extract_technical_spec_requirements,
)
from agent.analysis.nodes.fail_safely import fail_safely
from agent.analysis.nodes.finalize_completed_analysis import finalize_completed_analysis
from agent.analysis.nodes.load_document import load_document
from agent.analysis.nodes.retry_invalid_subset import retry_invalid_subset
from agent.analysis.nodes.validate_analysis import (
    route_after_precondition,
    route_after_validation,
    validate_analysis,
)
from agent.analysis.state import AnalysisState


def build_analysis_graph():  # type: ignore[no-untyped-def]
    graph = StateGraph(AnalysisState)

    graph.add_node("load_document", load_document)
    graph.add_node("ensure_classification", ensure_classification)
    graph.add_node("extract_contract_terms", extract_contract_terms)
    graph.add_node(
        "extract_technical_spec_requirements", extract_technical_spec_requirements
    )
    graph.add_node("build_extraction_context", build_extraction_context)
    graph.add_node("extract_generic_analysis", extract_generic_analysis)
    graph.add_node("validate_analysis", validate_analysis)
    graph.add_node("retry_invalid_subset", retry_invalid_subset)
    graph.add_node("finalize_completed_analysis", finalize_completed_analysis)
    graph.add_node("fail_safely", fail_safely)

    graph.set_entry_point("load_document")

    graph.add_conditional_edges(
        "load_document",
        route_after_precondition,
        {"continue": "ensure_classification", "fail": "fail_safely"},
    )
    graph.add_conditional_edges(
        "ensure_classification",
        route_by_document_type,
        {
            "contract": "extract_contract_terms",
            "technical_specification": "extract_technical_spec_requirements",
            "generic": "build_extraction_context",
            "fail": "fail_safely",
        },
    )
    graph.add_edge("extract_contract_terms", "build_extraction_context")
    graph.add_edge("extract_technical_spec_requirements", "build_extraction_context")
    graph.add_edge("build_extraction_context", "extract_generic_analysis")
    graph.add_edge("extract_generic_analysis", "validate_analysis")

    graph.add_conditional_edges(
        "validate_analysis",
        route_after_validation,
        {
            "persist": "finalize_completed_analysis",
            "retry": "retry_invalid_subset",
            "fail": "fail_safely",
        },
    )
    graph.add_edge("retry_invalid_subset", "validate_analysis")

    graph.add_edge("finalize_completed_analysis", END)
    graph.add_edge("fail_safely", END)

    return graph.compile()


_COMPILED_GRAPH = None


async def run_analysis_graph(initial_state: AnalysisState) -> AnalysisState:
    """Invoke the compiled graph once. Cached at module scope: the graph is
    stateless (no checkpointer), so compiling it once and reusing it across
    calls avoids rebuilding it on every request."""
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_analysis_graph()
    return await _COMPILED_GRAPH.ainvoke(initial_state)  # type: ignore[no-any-return]
