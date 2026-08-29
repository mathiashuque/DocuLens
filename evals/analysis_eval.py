"""Reproducible generic-extraction evaluator.

Consumes stored predictions (`ExtractionEvalSample`) — never a real
provider — and reports item-level precision/recall/F1 for findings, dates,
and risks, evidence-validity rate, schema-valid completion rate, targeted-
retry success/failure behavior, and a false-positive rate on categories a
sample expects to be empty.

Matching rule (documented, deterministic): a predicted item matches an
expected item of the same category when they cite the same `source_page`
and the expected item's `evidence_contains` substring appears, after the
same conservative whitespace normalization classification/analysis
validation use, inside the predicted item's evidence text. Matching is
greedy: expected items are matched in order to the first unmatched
predicted item satisfying the rule, so no predicted item is double-counted.
"""

from dataclasses import dataclass, field

from agent.classification.validation import normalize_whitespace


class InvalidDatasetError(Exception):
    """The prediction set is malformed: duplicate/missing sample IDs."""


@dataclass(frozen=True)
class ExtractionEvalItem:
    source_page: int
    evidence: str
    valid: bool


@dataclass(frozen=True)
class ExtractionEvalExpectedItem:
    source_page: int
    evidence_contains: str


@dataclass(frozen=True)
class ExtractionEvalSample:
    sample_id: str
    schema_valid: bool = True
    retry_attempted: bool = False
    retry_succeeded: bool | None = None
    predicted_findings: tuple[ExtractionEvalItem, ...] = ()
    predicted_dates: tuple[ExtractionEvalItem, ...] = ()
    predicted_risks: tuple[ExtractionEvalItem, ...] = ()
    expected_findings: tuple[ExtractionEvalExpectedItem, ...] = ()
    expected_dates: tuple[ExtractionEvalExpectedItem, ...] = ()
    expected_risks: tuple[ExtractionEvalExpectedItem, ...] = ()


@dataclass(frozen=True)
class CategoryMetrics:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class ExtractionEvalReport:
    sample_count: int
    schema_valid_completion_rate: float
    evidence_validity_rate: float | None
    invalid_evidence_count: int
    retry_attempted_count: int
    retry_succeeded_count: int
    retry_failed_count: int
    findings: CategoryMetrics
    dates: CategoryMetrics
    risks: CategoryMetrics
    false_positive_rate_on_expected_empty: dict[str, float | None] = field(
        default_factory=dict
    )


def _match(
    predicted: tuple[ExtractionEvalItem, ...],
    expected: tuple[ExtractionEvalExpectedItem, ...],
) -> CategoryMetrics:
    normalized_predicted = [
        (item.source_page, normalize_whitespace(item.evidence)) for item in predicted
    ]
    matched_predicted_indices: set[int] = set()
    true_positives = 0

    for expected_item in expected:
        needle = normalize_whitespace(expected_item.evidence_contains)
        for index, (page, evidence) in enumerate(normalized_predicted):
            if index in matched_predicted_indices:
                continue
            if page == expected_item.source_page and needle in evidence:
                matched_predicted_indices.add(index)
                true_positives += 1
                break

    false_positives = len(predicted) - true_positives
    false_negatives = len(expected) - true_positives
    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives)
        else (1.0 if not expected else 0.0)
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives)
        else 1.0
    )
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return CategoryMetrics(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=f1,
    )


def _aggregate_category(
    samples: list[ExtractionEvalSample],
    predicted_attr: str,
    expected_attr: str,
) -> CategoryMetrics:
    all_predicted: list[ExtractionEvalItem] = []
    all_expected: list[ExtractionEvalExpectedItem] = []
    true_positives = false_positives = false_negatives = 0

    for sample in samples:
        predicted = getattr(sample, predicted_attr)
        expected = getattr(sample, expected_attr)
        metrics = _match(predicted, expected)
        true_positives += metrics.true_positives
        false_positives += metrics.false_positives
        false_negatives += metrics.false_negatives
        all_predicted.extend(predicted)
        all_expected.extend(expected)

    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives)
        else (1.0 if not all_expected else 0.0)
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives)
        else 1.0
    )
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return CategoryMetrics(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=f1,
    )


def _validate_samples(samples: list[ExtractionEvalSample]) -> None:
    if not samples:
        raise InvalidDatasetError("prediction set must not be empty")
    seen: set[str] = set()
    for sample in samples:
        if sample.sample_id in seen:
            raise InvalidDatasetError(f"duplicate sample id: {sample.sample_id}")
        seen.add(sample.sample_id)


def evaluate_extractions(
    samples: list[ExtractionEvalSample],
) -> ExtractionEvalReport:
    _validate_samples(samples)

    schema_valid_count = sum(1 for s in samples if s.schema_valid)
    schema_valid_completion_rate = schema_valid_count / len(samples)

    all_items = [
        item
        for sample in samples
        for item in (
            *sample.predicted_findings,
            *sample.predicted_dates,
            *sample.predicted_risks,
        )
    ]
    evidence_validity_rate = (
        sum(1 for item in all_items if item.valid) / len(all_items)
        if all_items
        else None
    )
    invalid_evidence_count = sum(1 for item in all_items if not item.valid)

    retry_attempted = [s for s in samples if s.retry_attempted]
    retry_succeeded_count = sum(1 for s in retry_attempted if s.retry_succeeded)
    retry_failed_count = sum(1 for s in retry_attempted if s.retry_succeeded is False)

    false_positive_rates: dict[str, float | None] = {}
    for category, predicted_attr, expected_attr in (
        ("findings", "predicted_findings", "expected_findings"),
        ("dates", "predicted_dates", "expected_dates"),
        ("risks", "predicted_risks", "expected_risks"),
    ):
        expected_empty_samples = [s for s in samples if not getattr(s, expected_attr)]
        false_positive_rates[category] = (
            sum(1 for s in expected_empty_samples if getattr(s, predicted_attr))
            / len(expected_empty_samples)
            if expected_empty_samples
            else None
        )

    return ExtractionEvalReport(
        sample_count=len(samples),
        schema_valid_completion_rate=schema_valid_completion_rate,
        evidence_validity_rate=evidence_validity_rate,
        invalid_evidence_count=invalid_evidence_count,
        retry_attempted_count=len(retry_attempted),
        retry_succeeded_count=retry_succeeded_count,
        retry_failed_count=retry_failed_count,
        findings=_aggregate_category(
            samples, "predicted_findings", "expected_findings"
        ),
        dates=_aggregate_category(samples, "predicted_dates", "expected_dates"),
        risks=_aggregate_category(samples, "predicted_risks", "expected_risks"),
        false_positive_rate_on_expected_empty=false_positive_rates,
    )
