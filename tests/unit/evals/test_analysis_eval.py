"""Analysis evaluator unit tests: metric calculations against known stored
predictions, invalid-input handling, and CI's stored/fake-only path."""

import pytest

from evals.analysis_eval import (
    ExtractionEvalExpectedItem,
    ExtractionEvalItem,
    ExtractionEvalSample,
    InvalidDatasetError,
    evaluate_extractions,
)


def test_exact_match_yields_perfect_precision_recall() -> None:
    sample = ExtractionEvalSample(
        sample_id="s1",
        predicted_findings=(
            ExtractionEvalItem(
                source_page=1, evidence="renews automatically", valid=True
            ),
        ),
        expected_findings=(
            ExtractionEvalExpectedItem(
                source_page=1, evidence_contains="renews automatically"
            ),
        ),
    )

    report = evaluate_extractions([sample])

    assert report.findings.precision == pytest.approx(1.0)
    assert report.findings.recall == pytest.approx(1.0)
    assert report.findings.f1 == pytest.approx(1.0)


def test_missed_expected_item_reduces_recall() -> None:
    sample = ExtractionEvalSample(
        sample_id="s1",
        predicted_findings=(),
        expected_findings=(
            ExtractionEvalExpectedItem(
                source_page=1, evidence_contains="renews automatically"
            ),
        ),
    )

    report = evaluate_extractions([sample])

    assert report.findings.recall == 0.0
    assert report.findings.true_positives == 0
    assert report.findings.false_negatives == 1


def test_unexpected_predicted_item_reduces_precision() -> None:
    sample = ExtractionEvalSample(
        sample_id="s1",
        predicted_findings=(
            ExtractionEvalItem(
                source_page=1, evidence="unexpected content", valid=True
            ),
        ),
        expected_findings=(),
    )

    report = evaluate_extractions([sample])

    assert report.findings.precision == 0.0
    assert report.findings.false_positives == 1


def test_wrong_page_does_not_match() -> None:
    sample = ExtractionEvalSample(
        sample_id="s1",
        predicted_findings=(
            ExtractionEvalItem(
                source_page=2, evidence="renews automatically", valid=True
            ),
        ),
        expected_findings=(
            ExtractionEvalExpectedItem(
                source_page=1, evidence_contains="renews automatically"
            ),
        ),
    )

    report = evaluate_extractions([sample])

    assert report.findings.true_positives == 0
    assert report.findings.false_positives == 1
    assert report.findings.false_negatives == 1


def test_evidence_validity_rate_and_invalid_count() -> None:
    sample = ExtractionEvalSample(
        sample_id="s1",
        predicted_findings=(
            ExtractionEvalItem(source_page=1, evidence="a", valid=True),
            ExtractionEvalItem(source_page=1, evidence="b", valid=False),
        ),
    )

    report = evaluate_extractions([sample])

    assert report.evidence_validity_rate == pytest.approx(0.5)
    assert report.invalid_evidence_count == 1


def test_schema_valid_completion_rate() -> None:
    samples = [
        ExtractionEvalSample(sample_id="s1", schema_valid=True),
        ExtractionEvalSample(sample_id="s2", schema_valid=False),
    ]

    report = evaluate_extractions(samples)

    assert report.schema_valid_completion_rate == pytest.approx(0.5)


def test_retry_success_and_failure_counted() -> None:
    samples = [
        ExtractionEvalSample(
            sample_id="s1", retry_attempted=True, retry_succeeded=True
        ),
        ExtractionEvalSample(
            sample_id="s2", retry_attempted=True, retry_succeeded=False
        ),
        ExtractionEvalSample(sample_id="s3", retry_attempted=False),
    ]

    report = evaluate_extractions(samples)

    assert report.retry_attempted_count == 2
    assert report.retry_succeeded_count == 1
    assert report.retry_failed_count == 1


def test_false_positive_rate_on_expected_empty_category() -> None:
    samples = [
        ExtractionEvalSample(
            sample_id="s1",
            expected_findings=(),
            predicted_findings=(
                ExtractionEvalItem(source_page=1, evidence="hallucinated", valid=True),
            ),
        ),
        ExtractionEvalSample(
            sample_id="s2", expected_findings=(), predicted_findings=()
        ),
    ]

    report = evaluate_extractions(samples)

    assert report.false_positive_rate_on_expected_empty["findings"] == pytest.approx(
        0.5
    )


def test_false_positive_rate_is_none_when_no_expected_empty_samples() -> None:
    sample = ExtractionEvalSample(
        sample_id="s1",
        expected_findings=(
            ExtractionEvalExpectedItem(source_page=1, evidence_contains="x"),
        ),
    )

    report = evaluate_extractions([sample])

    assert report.false_positive_rate_on_expected_empty["findings"] is None


def test_duplicate_sample_ids_fail_visibly() -> None:
    samples = [
        ExtractionEvalSample(sample_id="dup"),
        ExtractionEvalSample(sample_id="dup"),
    ]

    with pytest.raises(InvalidDatasetError):
        evaluate_extractions(samples)


def test_empty_prediction_set_fails_visibly() -> None:
    with pytest.raises(InvalidDatasetError):
        evaluate_extractions([])
