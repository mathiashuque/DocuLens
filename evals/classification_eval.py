"""Reproducible classification evaluator.

Consumes stored predictions (`ClassificationEvalSample`), or an injected
classifier via `run_classification_eval`, and reports accuracy, per-class
accuracy/support, a confusion matrix, generic fallback rate, evidence-validity
rate, and failure accounting. Never calls a real provider itself; CI only
exercises this module with stored/fake predictions.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from agent.classification.taxonomy import ALLOWED_DOCUMENT_TYPES, DocumentType


class InvalidDatasetError(Exception):
    """The dataset or prediction set is malformed: duplicate/missing IDs or
    an expected/predicted label outside the supported taxonomy."""


@dataclass(frozen=True)
class ClassificationEvalDatasetItem:
    """One labeled evaluation example. `text` is synthetic/permissive only."""

    sample_id: str
    text: str
    expected_type: DocumentType
    is_prompt_injection: bool = False


@dataclass(frozen=True)
class ClassificationEvalSample:
    """One stored prediction to score against its expected label."""

    sample_id: str
    expected_type: DocumentType
    predicted_type: DocumentType | None = None
    evidence_valid: bool | None = None
    failed: bool = False


@dataclass(frozen=True)
class ClassificationEvalReport:
    sample_count: int
    failure_count: int
    accuracy: float
    per_class: dict[str, dict[str, float]]
    confusion_matrix: dict[str, dict[str, int]]
    generic_fallback_rate: float | None
    evidence_validity_rate: float | None
    failures: tuple[str, ...] = field(default_factory=tuple)


def _validate_samples(samples: list[ClassificationEvalSample]) -> None:
    seen: set[str] = set()
    for sample in samples:
        if sample.sample_id in seen:
            raise InvalidDatasetError(f"duplicate sample id: {sample.sample_id}")
        seen.add(sample.sample_id)
        if sample.expected_type not in ALLOWED_DOCUMENT_TYPES:
            raise InvalidDatasetError(
                f"{sample.sample_id}: invalid expected_type {sample.expected_type!r}"
            )
        if (
            sample.predicted_type is not None
            and sample.predicted_type not in ALLOWED_DOCUMENT_TYPES
        ):
            raise InvalidDatasetError(
                f"{sample.sample_id}: invalid predicted_type {sample.predicted_type!r}"
            )
    if not samples:
        raise InvalidDatasetError("dataset/prediction set must not be empty")


def evaluate_classifications(
    samples: list[ClassificationEvalSample],
) -> ClassificationEvalReport:
    _validate_samples(samples)

    scored = [sample for sample in samples if not sample.failed]
    failures = tuple(sample.sample_id for sample in samples if sample.failed)

    confusion_matrix: dict[str, dict[str, int]] = {
        expected: {predicted: 0 for predicted in ALLOWED_DOCUMENT_TYPES}
        for expected in ALLOWED_DOCUMENT_TYPES
    }
    per_class_correct: dict[str, int] = dict.fromkeys(ALLOWED_DOCUMENT_TYPES, 0)
    per_class_support: dict[str, int] = dict.fromkeys(ALLOWED_DOCUMENT_TYPES, 0)

    correct = 0
    for sample in scored:
        assert sample.predicted_type is not None  # not failed => has a prediction
        confusion_matrix[sample.expected_type][sample.predicted_type] += 1
        per_class_support[sample.expected_type] += 1
        if sample.predicted_type == sample.expected_type:
            correct += 1
            per_class_correct[sample.expected_type] += 1

    accuracy = correct / len(scored) if scored else 0.0
    per_class: dict[str, dict[str, float]] = {
        document_type: {
            "accuracy": (
                per_class_correct[document_type] / per_class_support[document_type]
                if per_class_support[document_type]
                else 0.0
            ),
            "support": float(per_class_support[document_type]),
        }
        for document_type in ALLOWED_DOCUMENT_TYPES
    }

    non_generic_expected = [
        sample for sample in scored if sample.expected_type != "generic"
    ]
    generic_fallback_rate = (
        sum(1 for s in non_generic_expected if s.predicted_type == "generic")
        / len(non_generic_expected)
        if non_generic_expected
        else None
    )

    evidence_scored = [s for s in scored if s.evidence_valid is not None]
    evidence_validity_rate = (
        sum(1 for s in evidence_scored if s.evidence_valid) / len(evidence_scored)
        if evidence_scored
        else None
    )

    return ClassificationEvalReport(
        sample_count=len(samples),
        failure_count=len(failures),
        accuracy=accuracy,
        per_class=per_class,
        confusion_matrix=confusion_matrix,
        generic_fallback_rate=generic_fallback_rate,
        evidence_validity_rate=evidence_validity_rate,
        failures=failures,
    )


ClassifierCallable = Callable[
    [ClassificationEvalDatasetItem], Awaitable[ClassificationEvalSample]
]


async def run_classification_eval(
    dataset: list[ClassificationEvalDatasetItem],
    classify_fn: ClassifierCallable,
) -> ClassificationEvalReport:
    """Run an injected async classifier over the dataset and score it.

    `classify_fn` is caller-provided: a fake in tests, or a real-model call
    site in an explicit, manual, opt-in evaluation script. This function
    itself never constructs a provider or makes a network call.
    """
    samples: list[ClassificationEvalSample] = []
    for item in dataset:
        samples.append(await classify_fn(item))
    return evaluate_classifications(samples)
