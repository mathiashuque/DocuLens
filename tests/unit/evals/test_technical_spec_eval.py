"""Technical-spec evaluator unit tests: metric calculations against known
stored predictions, invalid-input handling, and CI's stored/fake-only
path."""

import pytest

from evals.analysis_eval import ExtractionEvalExpectedItem, ExtractionEvalItem
from evals.technical_spec_eval import (
    InvalidDatasetError,
    TechnicalSpecEvalSample,
    evaluate_technical_spec_extractions,
)


def test_exact_match_yields_perfect_precision_recall() -> None:
    sample = TechnicalSpecEvalSample(
        sample_id="s1",
        predicted_functional=(
            ExtractionEvalItem(
                source_page=8, evidence="FR-12: revoke sessions", valid=True
            ),
        ),
        expected_functional=(
            ExtractionEvalExpectedItem(
                source_page=8, evidence_contains="FR-12: revoke sessions"
            ),
        ),
    )

    report = evaluate_technical_spec_extractions([sample])

    assert report.functional.precision == pytest.approx(1.0)
    assert report.functional.recall == pytest.approx(1.0)
    assert report.functional.f1 == pytest.approx(1.0)


def test_missed_expected_security_requirement_reduces_recall() -> None:
    sample = TechnicalSpecEvalSample(
        sample_id="s1",
        expected_security=(
            ExtractionEvalExpectedItem(source_page=1, evidence_contains="encrypt"),
        ),
    )

    report = evaluate_technical_spec_extractions([sample])

    assert report.security.recall == 0.0
    assert report.security.false_negatives == 1


def test_macro_requirement_f1_averages_the_four_categories() -> None:
    sample = TechnicalSpecEvalSample(
        sample_id="s1",
        predicted_functional=(
            ExtractionEvalItem(source_page=1, evidence="e", valid=True),
        ),
        expected_functional=(
            ExtractionEvalExpectedItem(source_page=1, evidence_contains="e"),
        ),
    )
    report = evaluate_technical_spec_extractions([sample])
    # functional f1 == 1.0, other three categories have no expected/predicted
    # items so also default to f1 == 1.0 (perfect vacuous match).
    assert report.macro_requirement_f1 == pytest.approx(1.0)


def test_micro_requirements_pools_all_four_categories() -> None:
    sample = TechnicalSpecEvalSample(
        sample_id="s1",
        predicted_functional=(
            ExtractionEvalItem(source_page=1, evidence="a", valid=True),
        ),
        expected_functional=(
            ExtractionEvalExpectedItem(source_page=1, evidence_contains="a"),
        ),
        predicted_security=(
            ExtractionEvalItem(source_page=2, evidence="b", valid=True),
        ),
        expected_security=(),
    )
    report = evaluate_technical_spec_extractions([sample])
    assert report.micro_requirements.true_positives == 1
    assert report.micro_requirements.false_positives == 1


def test_schema_valid_completion_rate() -> None:
    samples = [
        TechnicalSpecEvalSample(sample_id="s1", schema_valid=True),
        TechnicalSpecEvalSample(sample_id="s2", schema_valid=False),
    ]
    report = evaluate_technical_spec_extractions(samples)
    assert report.schema_valid_completion_rate == pytest.approx(0.5)


def test_evidence_validity_rate_counts_invalid_items() -> None:
    sample = TechnicalSpecEvalSample(
        sample_id="s1",
        predicted_constraints=(
            ExtractionEvalItem(source_page=1, evidence="ok", valid=True),
            ExtractionEvalItem(source_page=1, evidence="bad", valid=False),
        ),
    )
    report = evaluate_technical_spec_extractions([sample])
    assert report.evidence_validity_rate == pytest.approx(0.5)
    assert report.invalid_evidence_count == 1


def test_retry_counts() -> None:
    samples = [
        TechnicalSpecEvalSample(
            sample_id="s1", retry_attempted=True, retry_succeeded=True
        ),
        TechnicalSpecEvalSample(
            sample_id="s2", retry_attempted=True, retry_succeeded=False
        ),
        TechnicalSpecEvalSample(sample_id="s3", retry_attempted=False),
    ]
    report = evaluate_technical_spec_extractions(samples)
    assert report.retry_attempted_count == 2
    assert report.retry_succeeded_count == 1
    assert report.retry_failed_count == 1


def test_route_accuracy() -> None:
    samples = [
        TechnicalSpecEvalSample(
            sample_id="s1",
            expected_route="technical_specification",
            actual_route="technical_specification",
        ),
        TechnicalSpecEvalSample(
            sample_id="s2", expected_route="generic", actual_route="generic"
        ),
        TechnicalSpecEvalSample(
            sample_id="s3",
            expected_route="technical_specification",
            actual_route="generic",
        ),
    ]
    report = evaluate_technical_spec_extractions(samples)
    assert report.route_accuracy == pytest.approx(2 / 3)


def test_constraint_false_positive_rate_on_descriptive_mentions() -> None:
    samples = [
        TechnicalSpecEvalSample(
            sample_id="s1",
            descriptive_mention_present=True,
            constraints_predicted_from_descriptive_mention=1,
        ),
        TechnicalSpecEvalSample(
            sample_id="s2",
            descriptive_mention_present=True,
            constraints_predicted_from_descriptive_mention=0,
        ),
        TechnicalSpecEvalSample(sample_id="s3", descriptive_mention_present=False),
    ]
    report = evaluate_technical_spec_extractions(samples)
    assert (
        report.constraint_false_positive_rate_on_descriptive_mentions
        == pytest.approx(0.5)
    )


def test_category_overlap_correct_rate() -> None:
    samples = [
        TechnicalSpecEvalSample(
            sample_id="s1",
            category_overlap_present=True,
            category_overlap_resolved_correctly=True,
        ),
        TechnicalSpecEvalSample(
            sample_id="s2",
            category_overlap_present=True,
            category_overlap_resolved_correctly=False,
        ),
        TechnicalSpecEvalSample(sample_id="s3", category_overlap_present=False),
    ]
    report = evaluate_technical_spec_extractions(samples)
    assert report.category_overlap_correct_rate == pytest.approx(0.5)


def test_expected_empty_false_positive_rate() -> None:
    samples = [
        TechnicalSpecEvalSample(sample_id="s1", expected_constraints=()),
        TechnicalSpecEvalSample(
            sample_id="s2",
            expected_constraints=(),
            predicted_constraints=(
                ExtractionEvalItem(source_page=1, evidence="unexpected", valid=True),
            ),
        ),
    ]
    report = evaluate_technical_spec_extractions(samples)
    assert report.false_positive_rate_on_expected_empty["constraints"] == pytest.approx(
        0.5
    )


def test_duplicate_sample_ids_rejected() -> None:
    with pytest.raises(InvalidDatasetError):
        evaluate_technical_spec_extractions(
            [
                TechnicalSpecEvalSample(sample_id="dup"),
                TechnicalSpecEvalSample(sample_id="dup"),
            ]
        )


def test_empty_sample_set_rejected() -> None:
    with pytest.raises(InvalidDatasetError):
        evaluate_technical_spec_extractions([])
