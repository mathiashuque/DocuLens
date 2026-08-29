"""Classification evaluator unit tests: metric calculations against known
stored predictions, invalid-input handling, and CI's stored/fake-only path."""

import pytest

from evals.classification_eval import (
    ClassificationEvalSample,
    InvalidDatasetError,
    evaluate_classifications,
)


def test_known_predictions_produce_exact_accuracy_and_confusion_matrix() -> None:
    samples = [
        ClassificationEvalSample("s1", "contract", "contract", evidence_valid=True),
        ClassificationEvalSample("s2", "contract", "generic", evidence_valid=True),
        ClassificationEvalSample(
            "s3",
            "technical_specification",
            "technical_specification",
            evidence_valid=True,
        ),
        ClassificationEvalSample("s4", "generic", "generic", evidence_valid=True),
    ]

    report = evaluate_classifications(samples)

    assert report.sample_count == 4
    assert report.failure_count == 0
    assert report.accuracy == pytest.approx(3 / 4)
    assert report.confusion_matrix["contract"]["contract"] == 1
    assert report.confusion_matrix["contract"]["generic"] == 1
    assert (
        report.confusion_matrix["technical_specification"]["technical_specification"]
        == 1
    )
    assert report.confusion_matrix["generic"]["generic"] == 1


def test_per_class_accuracy_and_support() -> None:
    samples = [
        ClassificationEvalSample("s1", "contract", "contract"),
        ClassificationEvalSample("s2", "contract", "contract"),
        ClassificationEvalSample("s3", "contract", "generic"),
    ]

    report = evaluate_classifications(samples)

    assert report.per_class["contract"]["support"] == 3
    assert report.per_class["contract"]["accuracy"] == pytest.approx(2 / 3)
    assert report.per_class["generic"]["support"] == 0


def test_generic_fallback_rate_measures_non_generic_expected_routed_to_generic() -> (
    None
):
    samples = [
        ClassificationEvalSample("s1", "contract", "generic"),
        ClassificationEvalSample("s2", "contract", "contract"),
        ClassificationEvalSample("s3", "generic", "generic"),
    ]

    report = evaluate_classifications(samples)

    assert report.generic_fallback_rate == pytest.approx(1 / 2)


def test_evidence_validity_rate() -> None:
    samples = [
        ClassificationEvalSample("s1", "contract", "contract", evidence_valid=True),
        ClassificationEvalSample("s2", "contract", "contract", evidence_valid=False),
    ]

    report = evaluate_classifications(samples)

    assert report.evidence_validity_rate == pytest.approx(0.5)


def test_failures_are_excluded_from_accuracy_but_counted() -> None:
    samples = [
        ClassificationEvalSample("s1", "contract", "contract"),
        ClassificationEvalSample("s2", "contract", None, failed=True),
    ]

    report = evaluate_classifications(samples)

    assert report.sample_count == 2
    assert report.failure_count == 1
    assert report.accuracy == pytest.approx(1.0)
    assert "s2" in report.failures


def test_duplicate_sample_ids_fail_visibly() -> None:
    samples = [
        ClassificationEvalSample("dup", "contract", "contract"),
        ClassificationEvalSample("dup", "generic", "generic"),
    ]

    with pytest.raises(InvalidDatasetError):
        evaluate_classifications(samples)


def test_missing_samples_fail_visibly() -> None:
    with pytest.raises(InvalidDatasetError):
        evaluate_classifications([])


def test_invalid_expected_label_fails_visibly() -> None:
    samples = [ClassificationEvalSample("s1", "invoice", "contract")]  # type: ignore[arg-type]

    with pytest.raises(InvalidDatasetError):
        evaluate_classifications(samples)


def test_invalid_predicted_label_fails_visibly() -> None:
    samples = [ClassificationEvalSample("s1", "contract", "invoice")]  # type: ignore[arg-type]

    with pytest.raises(InvalidDatasetError):
        evaluate_classifications(samples)
