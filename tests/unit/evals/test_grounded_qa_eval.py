"""Grounded-QA evaluator tests: deterministic recorded-generation run,
metric correctness, reproducibility, and dataset validation. No test in
this module makes a network call or a real LLM request."""

import pytest

from evals.grounded_qa_eval import (
    InvalidGroundedQaDatasetError,
    evaluate_grounded_qa,
    load_grounded_qa_dataset,
)
from retrieval.providers.fake_provider import FakeEmbeddingProvider


@pytest.mark.asyncio
async def test_full_dataset_evaluation_is_reproducible() -> None:
    dataset = load_grounded_qa_dataset()
    provider = FakeEmbeddingProvider(dimension=32)

    first = await evaluate_grounded_qa(
        dataset,
        provider,
        embedding_provider_name="fake",
        embedding_model=provider.model,
    )
    second = await evaluate_grounded_qa(
        dataset,
        provider,
        embedding_provider_name="fake",
        embedding_model=provider.model,
    )

    assert first.status_accuracy == second.status_accuracy
    assert first.grounded_success_rate == second.grounded_success_rate
    assert first.recall_at == second.recall_at
    assert first.mrr == second.mrr


@pytest.mark.asyncio
async def test_dataset_has_a_mix_of_answered_and_insufficient_cases() -> None:
    dataset = load_grounded_qa_dataset()
    outcomes = {case.expected_outcome for case in dataset.cases}
    assert outcomes == {"answered", "insufficient_evidence"}


@pytest.mark.asyncio
async def test_invalid_citation_case_is_attributed_as_citation_validation_failure() -> (
    None
):
    dataset = load_grounded_qa_dataset()
    provider = FakeEmbeddingProvider(dimension=32)

    report = await evaluate_grounded_qa(
        dataset,
        provider,
        embedding_provider_name="fake",
        embedding_model=provider.model,
    )

    invalid_case = next(
        r
        for r in report.results
        if r.case_id == "gq-contract-b-invalid-citation-regression-check"
    )
    assert invalid_case.citation_valid is False
    assert invalid_case.failure_kind == "citation_validation"
    assert invalid_case.predicted_outcome == "insufficient_evidence"
    assert report.citation_validation_failure_count >= 1
    assert report.unsupported_or_invalid_citation_rate > 0.0


@pytest.mark.asyncio
async def test_correctly_grounded_case_succeeds() -> None:
    dataset = load_grounded_qa_dataset()
    provider = FakeEmbeddingProvider(dimension=32)

    report = await evaluate_grounded_qa(
        dataset,
        provider,
        embedding_provider_name="fake",
        embedding_model=provider.model,
    )

    termination_case = next(
        r for r in report.results if r.case_id == "gq-contract-a-termination"
    )
    assert termination_case.citation_valid is True
    assert termination_case.grounded_success is True
    assert termination_case.failure_kind is None


@pytest.mark.asyncio
async def test_no_relevant_chunk_case_reports_insufficient_evidence() -> None:
    dataset = load_grounded_qa_dataset()
    provider = FakeEmbeddingProvider(dimension=32)

    report = await evaluate_grounded_qa(
        dataset,
        provider,
        embedding_provider_name="fake",
        embedding_model=provider.model,
    )

    no_relevant_case = next(
        r for r in report.results if r.case_id == "gq-contract-a-no-relevant"
    )
    assert no_relevant_case.expected_outcome == "insufficient_evidence"
    assert no_relevant_case.predicted_outcome == "insufficient_evidence"


@pytest.mark.asyncio
async def test_report_keeps_recall_and_mrr_visible_from_shared_baseline() -> None:
    dataset = load_grounded_qa_dataset()
    provider = FakeEmbeddingProvider(dimension=32)

    report = await evaluate_grounded_qa(
        dataset,
        provider,
        embedding_provider_name="fake",
        embedding_model=provider.model,
    )

    assert set(report.recall_at) == {1, 3, 5}
    assert 0.0 <= report.mrr <= 1.0


def test_duplicate_case_id_is_rejected(tmp_path) -> None:
    import json

    bad = {
        "version": "bad",
        "cases": [
            {
                "case_id": "dup",
                "document_id": "contract-a",
                "question": "q",
                "expected_outcome": "insufficient_evidence",
                "category": "c",
            },
            {
                "case_id": "dup",
                "document_id": "contract-a",
                "question": "q2",
                "expected_outcome": "insufficient_evidence",
                "category": "c",
            },
        ],
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(InvalidGroundedQaDatasetError):
        load_grounded_qa_dataset(path)


def test_unknown_expected_outcome_is_rejected(tmp_path) -> None:
    import json

    bad = {
        "version": "bad",
        "cases": [
            {
                "case_id": "c1",
                "document_id": "contract-a",
                "question": "q",
                "expected_outcome": "maybe",
                "category": "c",
            }
        ],
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(InvalidGroundedQaDatasetError):
        load_grounded_qa_dataset(path)
