"""Reproducible contract-extraction evaluator.

Consumes stored predictions (`ContractEvalSample`) — never a real provider —
and reports item-level precision/recall/F1 for parties, obligations, payment
terms, and clauses; evidence-validity rate; schema-valid completion rate;
targeted-retry success/failure counts; contract-route accuracy from
validated classifications; and the obligation false-positive rate on
non-mandatory (aspirational/permissive) language.

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
    "ContractEvalReport",
    "ContractEvalSample",
    "ExtractionEvalExpectedItem",
    "ExtractionEvalItem",
    "InvalidDatasetError",
    "evaluate_contract_extractions",
]


@dataclass(frozen=True)
class ContractEvalSample:
    sample_id: str
    schema_valid: bool = True
    expected_route: str = "contract"
    actual_route: str = "contract"
    retry_attempted: bool = False
    retry_succeeded: bool | None = None

    predicted_parties: tuple[ExtractionEvalItem, ...] = ()
    predicted_obligations: tuple[ExtractionEvalItem, ...] = ()
    predicted_payment_terms: tuple[ExtractionEvalItem, ...] = ()
    predicted_clauses: tuple[ExtractionEvalItem, ...] = ()

    expected_parties: tuple[ExtractionEvalExpectedItem, ...] = ()
    expected_obligations: tuple[ExtractionEvalExpectedItem, ...] = ()
    expected_payment_terms: tuple[ExtractionEvalExpectedItem, ...] = ()
    expected_clauses: tuple[ExtractionEvalExpectedItem, ...] = ()

    # Non-mandatory (aspirational/permissive) language present in the
    # sample, and how many predicted obligations were incorrectly derived
    # from it — a direct measure of the obligation false-positive rate.
    non_mandatory_text_present: bool = False
    obligations_predicted_from_non_mandatory_text: int = 0


@dataclass(frozen=True)
class ContractEvalReport:
    sample_count: int
    schema_valid_completion_rate: float
    evidence_validity_rate: float | None
    invalid_evidence_count: int
    retry_attempted_count: int
    retry_succeeded_count: int
    retry_failed_count: int
    contract_route_accuracy: float
    obligation_false_positive_rate_on_non_mandatory_language: float | None
    parties: CategoryMetrics
    obligations: CategoryMetrics
    payment_terms: CategoryMetrics
    clauses: CategoryMetrics
    false_positive_rate_on_expected_empty: dict[str, float | None] = field(
        default_factory=dict
    )


def _aggregate_category(
    samples: list[ContractEvalSample],
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


def _validate_samples(samples: list[ContractEvalSample]) -> None:
    if not samples:
        raise InvalidDatasetError("prediction set must not be empty")
    seen: set[str] = set()
    for sample in samples:
        if sample.sample_id in seen:
            raise InvalidDatasetError(f"duplicate sample id: {sample.sample_id}")
        seen.add(sample.sample_id)


def evaluate_contract_extractions(
    samples: list[ContractEvalSample],
) -> ContractEvalReport:
    _validate_samples(samples)

    schema_valid_count = sum(1 for s in samples if s.schema_valid)
    schema_valid_completion_rate = schema_valid_count / len(samples)

    all_items = [
        item
        for sample in samples
        for item in (
            *sample.predicted_parties,
            *sample.predicted_obligations,
            *sample.predicted_payment_terms,
            *sample.predicted_clauses,
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

    contract_route_accuracy = sum(
        1 for s in samples if s.actual_route == s.expected_route
    ) / len(samples)

    non_mandatory_samples = [s for s in samples if s.non_mandatory_text_present]
    obligation_fp_rate = (
        sum(
            1
            for s in non_mandatory_samples
            if s.obligations_predicted_from_non_mandatory_text > 0
        )
        / len(non_mandatory_samples)
        if non_mandatory_samples
        else None
    )

    false_positive_rates: dict[str, float | None] = {}
    for category, predicted_attr, expected_attr in (
        ("parties", "predicted_parties", "expected_parties"),
        ("obligations", "predicted_obligations", "expected_obligations"),
        ("payment_terms", "predicted_payment_terms", "expected_payment_terms"),
        ("clauses", "predicted_clauses", "expected_clauses"),
    ):
        expected_empty_samples = [s for s in samples if not getattr(s, expected_attr)]
        false_positive_rates[category] = (
            sum(1 for s in expected_empty_samples if getattr(s, predicted_attr))
            / len(expected_empty_samples)
            if expected_empty_samples
            else None
        )

    return ContractEvalReport(
        sample_count=len(samples),
        schema_valid_completion_rate=schema_valid_completion_rate,
        evidence_validity_rate=evidence_validity_rate,
        invalid_evidence_count=invalid_evidence_count,
        retry_attempted_count=len(retry_attempted),
        retry_succeeded_count=retry_succeeded_count,
        retry_failed_count=retry_failed_count,
        contract_route_accuracy=contract_route_accuracy,
        obligation_false_positive_rate_on_non_mandatory_language=obligation_fp_rate,
        parties=_aggregate_category(samples, "predicted_parties", "expected_parties"),
        obligations=_aggregate_category(
            samples, "predicted_obligations", "expected_obligations"
        ),
        payment_terms=_aggregate_category(
            samples, "predicted_payment_terms", "expected_payment_terms"
        ),
        clauses=_aggregate_category(samples, "predicted_clauses", "expected_clauses"),
        false_positive_rate_on_expected_empty=false_positive_rates,
    )
