"""Run DocuLens's safe, deterministic evaluation baseline and publish its summary.

This command intentionally uses only checked-in synthetic fixtures, recorded QA
outputs, and the in-process fake embedding provider. It never reads provider
configuration or constructs a real provider client.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from evals.grounded_qa_eval import evaluate_grounded_qa, load_grounded_qa_dataset
from evals.retrieval_eval import evaluate_retrieval, load_retrieval_dataset
from retrieval.providers.fake_provider import FakeEmbeddingProvider

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "evals" / "results" / "baseline-v1.json"
DEFAULT_REPORT = ROOT / "docs" / "evaluation.md"
DATASETS = ("classification_v1", "analysis_v1", "contract_v1", "technical_spec_v1")


def _dataset_metadata(name: str) -> dict[str, Any]:
    path = ROOT / "evals" / "datasets" / f"{name}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw.get("samples", raw.get("cases", []))
    if not isinstance(rows, list) or not rows or raw.get("version") != name:
        raise ValueError(f"invalid dataset: {path.relative_to(ROOT)}")
    types = sorted(
        {str(row["document_type"]) for row in rows if "document_type" in row}
    )
    return {
        "path": str(path.relative_to(ROOT)),
        "version": name,
        "case_count": len(rows),
        "document_types": types,
    }


async def build_result() -> dict[str, Any]:
    metadata = {name: _dataset_metadata(name) for name in DATASETS}
    retrieval_dataset = load_retrieval_dataset()
    provider = FakeEmbeddingProvider(dimension=32)
    retrieval = await evaluate_retrieval(
        retrieval_dataset,
        provider,
        embedding_provider_name="fake",
        embedding_model=provider.model,
        dimension=32,
    )
    qa = await evaluate_grounded_qa(
        load_grounded_qa_dataset(),
        FakeEmbeddingProvider(dimension=32),
        embedding_provider_name="fake",
        embedding_model="fake-deterministic-v1",
    )
    suites: list[dict[str, Any]] = []
    for name, task in (
        ("classification_v1", "classification"),
        ("analysis_v1", "generic_extraction"),
        ("contract_v1", "contract_extraction"),
        ("technical_spec_v1", "technical_specification_extraction"),
    ):
        suites.append(
            {
                "name": task,
                "task": task,
                "dataset": metadata[name],
                "evaluator_version": "existing-unit-evaluator-v1",
                "prediction_source": "none",
                "metrics": None,
                "failures": [],
                "limitations": [
                    "The checked-in fixture has labels/validation scenarios but no independent stored predictions; existing metrics test evaluator correctness and are not publishable pipeline-quality measurements."
                ],
            }
        )
    suites.extend(
        [
            {
                "name": "retrieval",
                "task": "retrieval",
                "dataset": {
                    "path": "evals/datasets/retrieval_v1.json",
                    "version": retrieval.dataset_version,
                    "case_count": retrieval.sample_count,
                    "document_types": sorted(
                        {d.document_type for d in retrieval_dataset.documents}
                    ),
                },
                "evaluator_version": retrieval.chunker_version,
                "prediction_source": "deterministic_fake_embedding",
                "metrics": {
                    "recall_at": retrieval.recall_at,
                    "mrr": retrieval.mrr,
                    "scored_query_count": retrieval.scored_sample_count,
                    "no_relevant_query_count": retrieval.no_relevant_query_count,
                    "failure_count": retrieval.failure_count,
                    "embedding_calls": {
                        "documents": retrieval.embed_document_calls,
                        "queries": retrieval.embed_query_calls,
                    },
                    "provenance": {
                        "valid": retrieval.provenance_valid_count,
                        "invalid": retrieval.provenance_invalid_count,
                        "cross_document_leakage": retrieval.cross_document_leakage_count,
                    },
                },
                "failures": list(retrieval.failures),
                "limitations": [
                    "Latency is deliberately omitted: in-process timing is not production latency."
                ],
            },
            {
                "name": "grounded_qa",
                "task": "grounded_qa",
                "dataset": {
                    "path": "evals/datasets/grounded_qa_v1.json",
                    "version": qa.dataset_version,
                    "case_count": qa.sample_count,
                    "document_types": [],
                },
                "evaluator_version": "recorded-grounded-qa-v1",
                "prediction_source": "recorded_provider_output",
                "metrics": {
                    "grounded_success_rate": qa.grounded_success_rate,
                    "insufficient_recall": qa.insufficient_recall,
                    "citation_validity_rate": qa.citation_validity_rate,
                    "unsupported_or_invalid_citation_rate": qa.unsupported_or_invalid_citation_rate,
                    "citation_validation_failure_count": qa.citation_validation_failure_count,
                    "retrieval_recall_at": qa.recall_at,
                    "retrieval_mrr": qa.mrr,
                },
                "failures": [],
                "limitations": [
                    "Recorded answers exercise workflow and citation enforcement, not live-model correctness or faithfulness."
                ],
            },
        ]
    )
    return {
        "schema_version": "baseline-v1",
        "mode": "deterministic_no_network_or_provider_calls",
        "command": "python -m evals.run_baselines --output evals/results/baseline-v1.json",
        "suites": suites,
        "complete": True,
    }


def render_report(result: dict[str, Any]) -> str:
    retrieval = next(s for s in result["suites"] if s["name"] == "retrieval")["metrics"]
    grounded_qa = next(s for s in result["suites"] if s["name"] == "grounded_qa")
    qa = grounded_qa["metrics"]
    recalls = "/".join(f"{retrieval['recall_at'][k]:.4f}" for k in (1, 3, 5))
    return f"""# Evaluation baselines

Run `python -m evals.run_baselines --output evals/results/baseline-v1.json`.

This is a deterministic, no-network harness over synthetic fixtures, fake embeddings, and recorded QA outputs—not a live-model benchmark.

| Suite | Dataset cases | Prediction source | Measured results |
| --- | ---: | --- | --- |
| Retrieval | {retrieval["scored_query_count"]} | deterministic fake embedding | Recall@1/3/5: {recalls}; MRR: {retrieval["mrr"]:.4f} |
| Grounded QA | {grounded_qa["dataset"]["case_count"]} | recorded output | grounded success: {qa["grounded_success_rate"]:.4f}; citation validity: {qa["citation_validity_rate"]:.4f}; invalid citation rate: {qa["unsupported_or_invalid_citation_rate"]:.4f} |

## Methodology and limitations

Retrieval preserves chunk/page provenance and reports cross-document leakage separately. Grounded-QA validates recorded citations against retrieved context; it does not measure live-model answer quality. Classification and extraction fixtures currently support evaluator/validator correctness only because they have no independent stored predictions; no quality score is published for them.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(build_result())
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    report = render_report(result)
    if args.check:
        return (
            0
            if args.output.read_text() == payload and args.report.read_text() == report
            else 1
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload)
    args.report.write_text(report)
    print(f"baseline: {len(result['suites'])} suites; deterministic no-network mode")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
