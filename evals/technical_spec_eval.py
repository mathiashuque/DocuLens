"""Reproducible technical-specification-extraction evaluator.

Consumes stored predictions (`TechnicalSpecEvalSample`) — never a real
provider — and reports per-category (functional/non_functional/security/
integration) precision/recall/F1 for requirements plus macro/micro
aggregates, constraint/dependency precision/recall/F1, evidence-validity
rate, schema-valid completion rate, targeted-retry success/failure counts,
specialized-route accuracy from validated classifications, the constraint
false-positive rate on merely descriptive technology mentions, and the rate
at which the documented category-precedence rule correctly resolved an
overlapping security/functional-style statement to a single category.

Reuses `ExtractionEvalItem`/`ExtractionEvalExpectedItem`/`CategoryMetrics`
and the same documented greedy same-page/substring matching rule from
`evals.analysis_eval` rather than redefining an incompatible metric shape.
"""

from dataclasses import dataclass, field

from evals.analysis_eval import (
    CategoryMetrics,
    ExtractionEvalExpectedItem,
    ExtractionEvalItem,
    InvalidDatasetError,
    match_item,
)

__all__ = [
    "CategoryMetrics",
    "ExtractionEvalExpectedItem",
    "ExtractionEvalItem",
    "InvalidDatasetError",
    "TechnicalSpecEvalReport",
    "TechnicalSpecEvalSample",
    "evaluate_technical_spec_extractions",
]

_REQUIREMENT_CATEGORIES: tuple[str, ...] = (
    "functional",
    "non_functional",
    "security",
    "integration",
)


@dataclass(frozen=True)
class TechnicalSpecEvalSample:
    sample_id: str
    schema_valid: bool = True
    expected_route: str = "technical_specification"
    actual_route: str = "technical_specification"
    retry_attempted: bool = False
    retry_succeeded: bool | None = None

    predicted_functional: tuple[ExtractionEvalItem, ...] = ()
    predicted_non_functional: tuple[ExtractionEvalItem, ...] = ()
    predicted_security: tuple[ExtractionEvalItem, ...] = ()
    predicted_integration: tuple[ExtractionEvalItem, ...] = ()
    predicted_constraints: tuple[ExtractionEvalItem, ...] = ()
    predicted_dependencies: tuple[ExtractionEvalItem, ...] = ()

    expected_functional: tuple[ExtractionEvalExpectedItem, ...] = ()
    expected_non_functional: tuple[ExtractionEvalExpectedItem, ...] = ()
    expected_security: tuple[ExtractionEvalExpectedItem, ...] = ()
    expected_integration: tuple[ExtractionEvalExpectedItem, ...] = ()
    expected_constraints: tuple[ExtractionEvalExpectedItem, ...] = ()
    expected_dependencies: tuple[ExtractionEvalExpectedItem, ...] = ()

    # A technology/product mentioned only descriptively, and how many
    # predicted constraints were incorrectly derived from it — a direct
    # measure of the constraint false-positive rate.
    descriptive_mention_present: bool = False
    constraints_predicted_from_descriptive_mention: int = 0

    # A statement that could plausibly fit more than one requirement
    # category (e.g. security language that also describes behavior), and
    # whether the documented precedence rule resolved it to exactly one
    # category in the prediction being evaluated.
    category_overlap_present: bool = False
    category_overlap_resolved_correctly: bool | None = None


@dataclass(frozen=True)
class TechnicalSpecEvalReport:
    sample_count: int
    schema_valid_completion_rate: float
    evidence_validity_rate: float | None
    invalid_evidence_count: int
    retry_attempted_count: int
    retry_succeeded_count: int
    retry_failed_count: int
    route_accuracy: float
    constraint_false_positive_rate_on_descriptive_mentions: float | None
    category_overlap_correct_rate: float | None
    functional: CategoryMetrics
    non_functional: CategoryMetrics
    security: CategoryMetrics
    integration: CategoryMetrics
    macro_requirement_f1: float
    micro_requirements: CategoryMetrics
    constraints: CategoryMetrics
    dependencies: CategoryMetrics
    false_positive_rate_on_expected_empty: dict[str, float | None] = field(
        default_factory=dict
    )


def _aggregate_category(
    samples: list[TechnicalSpecEvalSample],
    predicted_attr: str,
    expected_attr: str,
) -> CategoryMetrics:
    true_positives = false_positives = false_negatives = 0
    for sample in samples:
        metrics = match_item(
            getattr(sample, predicted_attr), getattr(sample, expected_attr)
        )
        true_positives += metrics.true_positives
        false_positives += metrics.false_positives
        false_negatives += metrics.false_negatives

    total_expected = sum(len(getattr(s, expected_attr)) for s in samples)
    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives)
        else (1.0 if not total_expected else 0.0)
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


def _validate_samples(samples: list[TechnicalSpecEvalSample]) -> None:
    if not samples:
        raise InvalidDatasetError("prediction set must not be empty")
    seen: set[str] = set()
    for sample in samples:
        if sample.sample_id in seen:
            raise InvalidDatasetError(f"duplicate sample id: {sample.sample_id}")
        seen.add(sample.sample_id)


def evaluate_technical_spec_extractions(
    samples: list[TechnicalSpecEvalSample],
) -> TechnicalSpecEvalReport:
    _validate_samples(samples)

    schema_valid_count = sum(1 for s in samples if s.schema_valid)
    schema_valid_completion_rate = schema_valid_count / len(samples)

    all_items = [
        item
        for sample in samples
        for item in (
            *sample.predicted_functional,
            *sample.predicted_non_functional,
            *sample.predicted_security,
            *sample.predicted_integration,
            *sample.predicted_constraints,
            *sample.predicted_dependencies,
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

    route_accuracy = sum(
        1 for s in samples if s.actual_route == s.expected_route
    ) / len(samples)

    descriptive_samples = [s for s in samples if s.descriptive_mention_present]
    constraint_fp_rate = (
        sum(
            1
            for s in descriptive_samples
            if s.constraints_predicted_from_descriptive_mention > 0
        )
        / len(descriptive_samples)
        if descriptive_samples
        else None
    )

    overlap_samples = [s for s in samples if s.category_overlap_present]
    overlap_correct_rate = (
        sum(1 for s in overlap_samples if s.category_overlap_resolved_correctly)
        / len(overlap_samples)
        if overlap_samples
        else None
    )

    category_metrics = {
        category: _aggregate_category(
            samples, f"predicted_{category}", f"expected_{category}"
        )
        for category in _REQUIREMENT_CATEGORIES
    }
    macro_requirement_f1 = sum(m.f1 for m in category_metrics.values()) / len(
        category_metrics
    )

    micro_tp = sum(m.true_positives for m in category_metrics.values())
    micro_fp = sum(m.false_positives for m in category_metrics.values())
    micro_fn = sum(m.false_negatives for m in category_metrics.values())
    micro_precision = micro_tp / (micro_tp + micro_fp) if (micro_tp + micro_fp) else 1.0
    micro_recall = micro_tp / (micro_tp + micro_fn) if (micro_tp + micro_fn) else 1.0
    micro_f1 = (
        2 * micro_precision * micro_recall / (micro_precision + micro_recall)
        if (micro_precision + micro_recall)
        else 0.0
    )
    micro_requirements = CategoryMetrics(
        true_positives=micro_tp,
        false_positives=micro_fp,
        false_negatives=micro_fn,
        precision=micro_precision,
        recall=micro_recall,
        f1=micro_f1,
    )

    false_positive_rates: dict[str, float | None] = {}
    for category, predicted_attr, expected_attr in (
        ("functional", "predicted_functional", "expected_functional"),
        ("non_functional", "predicted_non_functional", "expected_non_functional"),
        ("security", "predicted_security", "expected_security"),
        ("integration", "predicted_integration", "expected_integration"),
        ("constraints", "predicted_constraints", "expected_constraints"),
        ("dependencies", "predicted_dependencies", "expected_dependencies"),
    ):
        expected_empty_samples = [s for s in samples if not getattr(s, expected_attr)]
        false_positive_rates[category] = (
            sum(1 for s in expected_empty_samples if getattr(s, predicted_attr))
            / len(expected_empty_samples)
            if expected_empty_samples
            else None
        )

    return TechnicalSpecEvalReport(
        sample_count=len(samples),
        schema_valid_completion_rate=schema_valid_completion_rate,
        evidence_validity_rate=evidence_validity_rate,
        invalid_evidence_count=invalid_evidence_count,
        retry_attempted_count=len(retry_attempted),
        retry_succeeded_count=retry_succeeded_count,
        retry_failed_count=retry_failed_count,
        route_accuracy=route_accuracy,
        constraint_false_positive_rate_on_descriptive_mentions=constraint_fp_rate,
        category_overlap_correct_rate=overlap_correct_rate,
        functional=category_metrics["functional"],
        non_functional=category_metrics["non_functional"],
        security=category_metrics["security"],
        integration=category_metrics["integration"],
        macro_requirement_f1=macro_requirement_f1,
        micro_requirements=micro_requirements,
        constraints=_aggregate_category(
            samples, "predicted_constraints", "expected_constraints"
        ),
        dependencies=_aggregate_category(
            samples, "predicted_dependencies", "expected_dependencies"
        ),
        false_positive_rate_on_expected_empty=false_positive_rates,
    )
