"""Contract evaluator unit tests: metric calculations against known stored
predictions, invalid-input handling, and CI's stored/fake-only path."""

import pytest

from evals.analysis_eval import ExtractionEvalExpectedItem, ExtractionEvalItem
from evals.contract_eval import (
    ContractEvalSample,
    InvalidDatasetError,
    evaluate_contract_extractions,
)


def test_exact_match_yields_perfect_precision_recall() -> None:
    sample = ContractEvalSample(
        sample_id="s1",
        predicted_parties=(
            ExtractionEvalItem(
                source_page=1, evidence="Northstar Hosting Ltd.", valid=True
            ),
        ),
        expected_parties=(
            ExtractionEvalExpectedItem(
                source_page=1, evidence_contains="Northstar Hosting Ltd."
            ),
        ),
    )

    report = evaluate_contract_extractions([sample])

    assert report.parties.precision == pytest.approx(1.0)
    assert report.parties.recall == pytest.approx(1.0)
    assert report.parties.f1 == pytest.approx(1.0)


def test_missed_expected_obligation_reduces_recall() -> None:
    sample = ContractEvalSample(
        sample_id="s1",
        expected_obligations=(
            ExtractionEvalExpectedItem(source_page=1, evidence_contains="shall pay"),
        ),
    )

    report = evaluate_contract_extractions([sample])

    assert report.obligations.recall == 0.0
    assert report.obligations.false_negatives == 1


def test_schema_valid_completion_rate() -> None:
    samples = [
        ContractEvalSample(sample_id="s1", schema_valid=True),
        ContractEvalSample(sample_id="s2", schema_valid=False),
    ]
    report = evaluate_contract_extractions(samples)
    assert report.schema_valid_completion_rate == pytest.approx(0.5)


def test_evidence_validity_rate_counts_invalid_items() -> None:
    sample = ContractEvalSample(
        sample_id="s1",
        predicted_parties=(
            ExtractionEvalItem(source_page=1, evidence="ok", valid=True),
            ExtractionEvalItem(source_page=1, evidence="bad", valid=False),
        ),
    )
    report = evaluate_contract_extractions([sample])
    assert report.evidence_validity_rate == pytest.approx(0.5)
    assert report.invalid_evidence_count == 1


def test_retry_counts() -> None:
    samples = [
        ContractEvalSample(sample_id="s1", retry_attempted=True, retry_succeeded=True),
        ContractEvalSample(sample_id="s2", retry_attempted=True, retry_succeeded=False),
        ContractEvalSample(sample_id="s3", retry_attempted=False),
    ]
    report = evaluate_contract_extractions(samples)
    assert report.retry_attempted_count == 2
    assert report.retry_succeeded_count == 1
    assert report.retry_failed_count == 1


def test_contract_route_accuracy() -> None:
    samples = [
        ContractEvalSample(
            sample_id="s1", expected_route="contract", actual_route="contract"
        ),
        ContractEvalSample(
            sample_id="s2", expected_route="generic", actual_route="generic"
        ),
        ContractEvalSample(
            sample_id="s3", expected_route="contract", actual_route="generic"
        ),
    ]
    report = evaluate_contract_extractions(samples)
    assert report.contract_route_accuracy == pytest.approx(2 / 3)


def test_obligation_false_positive_rate_on_non_mandatory_language() -> None:
    samples = [
        ContractEvalSample(
            sample_id="s1",
            non_mandatory_text_present=True,
            obligations_predicted_from_non_mandatory_text=1,
        ),
        ContractEvalSample(
            sample_id="s2",
            non_mandatory_text_present=True,
            obligations_predicted_from_non_mandatory_text=0,
        ),
        ContractEvalSample(sample_id="s3", non_mandatory_text_present=False),
    ]
    report = evaluate_contract_extractions(samples)
    assert (
        report.obligation_false_positive_rate_on_non_mandatory_language
        == pytest.approx(0.5)
    )


def test_expected_empty_false_positive_rate() -> None:
    samples = [
        ContractEvalSample(sample_id="s1", expected_clauses=()),
        ContractEvalSample(
            sample_id="s2",
            expected_clauses=(),
            predicted_clauses=(
                ExtractionEvalItem(source_page=1, evidence="unexpected", valid=True),
            ),
        ),
    ]
    report = evaluate_contract_extractions(samples)
    assert report.false_positive_rate_on_expected_empty["clauses"] == pytest.approx(0.5)


def test_duplicate_sample_ids_rejected() -> None:
    with pytest.raises(InvalidDatasetError):
        evaluate_contract_extractions(
            [ContractEvalSample(sample_id="dup"), ContractEvalSample(sample_id="dup")]
        )


def test_empty_sample_set_rejected() -> None:
    with pytest.raises(InvalidDatasetError):
        evaluate_contract_extractions([])
