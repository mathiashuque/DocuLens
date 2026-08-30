"""Reproducible grounded-QA evaluator.

Reuses the versioned retrieval baseline dataset's documents, pages, and
chunking exactly (`evals/datasets/retrieval_v1.json` via
`evals.retrieval_eval`), plus a small versioned grounded-QA case file
(`evals/datasets/grounded_qa_v1.json`) of hand-authored, recorded expected
generation outputs. No real LLM call is ever made: each case's recorded
answer/citations stand in for "generation," and are run through the exact
same production `retrieval.citation_validation.validate_candidate` and
`retrieval.grounded_qa.build_context` the API service uses, so a citation
validator regression or dataset drift is caught the same way it would be in
the real pipeline. Recall@K/MRR are reported from the same underlying
retrieval run (via `evals.retrieval_eval.evaluate_retrieval`) so a
grounded-QA change can never silently hide a retrieval regression.
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from agent.grounded_qa.types import CitationCandidate, GroundedAnswerCandidate
from evals.retrieval_eval import (
    IndexedDocument,
    RetrievalEvalDataset,
    evaluate_retrieval,
    index_dataset_documents,
    load_retrieval_dataset,
    search_indexed_document,
)
from retrieval.chunking import Chunk
from retrieval.citation_validation import validate_candidate
from retrieval.embedding import EmbeddingProvider
from retrieval.grounded_qa import build_context

DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parent / "datasets" / "grounded_qa_v1.json"
)
DEFAULT_TOP_K = 5


class InvalidGroundedQaDatasetError(Exception):
    """The grounded-QA dataset is malformed: duplicate case IDs or an
    unknown expected outcome."""


@dataclass(frozen=True)
class RecordedCitation:
    page: int
    evidence: str


@dataclass(frozen=True)
class GroundedQaCase:
    case_id: str
    document_id: str
    question: str
    expected_outcome: str
    expected_pages: tuple[int, ...]
    recorded_answer: str
    recorded_citations: tuple[RecordedCitation, ...]
    required_answer_substrings: tuple[str, ...]
    category: str


@dataclass(frozen=True)
class GroundedQaDataset:
    version: str
    cases: list[GroundedQaCase]


_VALID_OUTCOMES = {"answered", "insufficient_evidence"}


def load_grounded_qa_dataset(
    path: Path = DEFAULT_DATASET_PATH,
) -> GroundedQaDataset:
    raw = json.loads(path.read_text())
    cases: list[GroundedQaCase] = []
    seen_ids: set[str] = set()
    for raw_case in raw["cases"]:
        case_id = raw_case["case_id"]
        if case_id in seen_ids:
            raise InvalidGroundedQaDatasetError(f"duplicate case_id: {case_id}")
        seen_ids.add(case_id)
        expected_outcome = raw_case["expected_outcome"]
        if expected_outcome not in _VALID_OUTCOMES:
            raise InvalidGroundedQaDatasetError(
                f"{case_id} has unknown expected_outcome: {expected_outcome!r}"
            )
        cases.append(
            GroundedQaCase(
                case_id=case_id,
                document_id=raw_case["document_id"],
                question=raw_case["question"],
                expected_outcome=expected_outcome,
                expected_pages=tuple(raw_case.get("expected_pages", [])),
                recorded_answer=raw_case.get("recorded_answer", ""),
                recorded_citations=tuple(
                    RecordedCitation(page=c["page"], evidence=c["evidence"])
                    for c in raw_case.get("recorded_citations", [])
                ),
                required_answer_substrings=tuple(
                    s.lower() for s in raw_case.get("required_answer_substrings", [])
                ),
                category=raw_case["category"],
            )
        )
    return GroundedQaDataset(version=raw["version"], cases=cases)


def _find_chunk_for_page(indexed: IndexedDocument, page: int) -> Chunk | None:
    for chunk in indexed.chunks:
        if chunk.page_start <= page <= chunk.page_end:
            return chunk
    return None


@dataclass(frozen=True)
class _RankedContextResult:
    chunk_id: uuid.UUID
    chunk_index: int
    text: str
    page_start: int
    page_end: int
    section_title: str | None
    section_path: list[str]


@dataclass(frozen=True)
class CaseEvalResult:
    case_id: str
    category: str
    expected_outcome: str
    predicted_outcome: str
    retrieval_hit: bool
    citation_valid: bool | None
    grounded_success: bool
    failure_kind: str | None
    latency_ms: int


@dataclass(frozen=True)
class GroundedQaEvalReport:
    dataset_version: str
    embedding_provider: str
    embedding_model: str
    sample_count: int
    status_accuracy: float
    insufficient_precision: float | None
    insufficient_recall: float | None
    citation_validity_rate: float
    grounded_success_rate: float
    unsupported_or_invalid_citation_rate: float
    retrieval_miss_count: int
    citation_validation_failure_count: int
    avg_latency_ms: float
    recall_at: dict[int, float]
    mrr: float
    results: tuple[CaseEvalResult, ...] = field(default_factory=tuple)


async def evaluate_grounded_qa(
    dataset: GroundedQaDataset,
    provider: EmbeddingProvider,
    *,
    embedding_provider_name: str,
    embedding_model: str,
    top_k: int = DEFAULT_TOP_K,
) -> GroundedQaEvalReport:
    retrieval_dataset: RetrievalEvalDataset = load_retrieval_dataset()
    indexed, _stats = await index_dataset_documents(retrieval_dataset, provider)
    pages_by_document = {
        document.document_id: {page.page_number: page.text for page in document.pages}
        for document in retrieval_dataset.documents
    }
    retrieval_report = await evaluate_retrieval(
        retrieval_dataset,
        provider,
        embedding_provider_name=embedding_provider_name,
        embedding_model=embedding_model,
        dimension=provider.dimension,
    )

    results: list[CaseEvalResult] = []
    for case in dataset.cases:
        started = time.perf_counter()
        indexed_document = indexed.get(case.document_id)
        document_pages = pages_by_document.get(case.document_id, {})
        if indexed_document is None:
            results.append(
                CaseEvalResult(
                    case_id=case.case_id,
                    category=case.category,
                    expected_outcome=case.expected_outcome,
                    predicted_outcome="insufficient_evidence",
                    retrieval_hit=False,
                    citation_valid=None,
                    grounded_success=False,
                    failure_kind="retrieval_miss",
                    latency_ms=0,
                )
            )
            continue

        embedded_query = await provider.embed_query(case.question)
        ranked = search_indexed_document(
            indexed_document, embedded_query.vector, top_k=top_k
        )
        context_items = build_context(
            [
                _RankedContextResult(
                    chunk_id=r.chunk.id,
                    chunk_index=r.chunk.chunk_index,
                    text=r.chunk.text,
                    page_start=r.chunk.page_start,
                    page_end=r.chunk.page_end,
                    section_title=r.chunk.section_title,
                    section_path=r.chunk.section_path,
                )
                for r in ranked
            ]
        )
        retrieved_pages = {
            page
            for item in context_items
            for page in range(item.page_start, item.page_end + 1)
        }
        retrieval_hit = (
            all(page in retrieved_pages for page in case.expected_pages)
            if case.expected_pages
            else True
        )
        latency_ms = int((time.perf_counter() - started) * 1000)

        if case.expected_outcome == "insufficient_evidence":
            candidate = GroundedAnswerCandidate(
                status="insufficient_evidence",
                answer=case.recorded_answer or "insufficient evidence",
                citations=[],
            )
            citation_valid: bool | None = None
        else:
            citations = []
            for recorded in case.recorded_citations:
                chunk = _find_chunk_for_page(indexed_document, recorded.page)
                if chunk is not None:
                    citations.append(
                        CitationCandidate(
                            chunk_id=str(chunk.id),
                            page=recorded.page,
                            evidence=recorded.evidence,
                        )
                    )
            candidate = GroundedAnswerCandidate(
                status="answered",
                answer=case.recorded_answer or "answer",
                citations=citations
                or [
                    CitationCandidate(
                        chunk_id=str(uuid.uuid4()), page=1, evidence="unresolvable"
                    )
                ],
            )
            validation = validate_candidate(
                candidate, context_items=context_items, document_pages=document_pages
            )
            citation_valid = validation.valid

        predicted_outcome = (
            "answered"
            if candidate.status == "answered" and citation_valid
            else "insufficient_evidence"
        )
        outcome_correct = predicted_outcome == case.expected_outcome
        required_facts_present = all(
            substring in case.recorded_answer.lower()
            for substring in case.required_answer_substrings
        )
        grounded_success = (
            outcome_correct
            and predicted_outcome == "answered"
            and retrieval_hit
            and required_facts_present
        )
        failure_kind = None
        if not retrieval_hit:
            failure_kind = "retrieval_miss"
        elif case.expected_outcome == "answered" and citation_valid is False:
            failure_kind = "citation_validation"

        results.append(
            CaseEvalResult(
                case_id=case.case_id,
                category=case.category,
                expected_outcome=case.expected_outcome,
                predicted_outcome=predicted_outcome,
                retrieval_hit=retrieval_hit,
                citation_valid=citation_valid,
                grounded_success=grounded_success,
                failure_kind=failure_kind,
                latency_ms=latency_ms,
            )
        )

    sample_count = len(results)
    status_correct = sum(
        1 for r in results if r.predicted_outcome == r.expected_outcome
    )
    status_accuracy = status_correct / sample_count if sample_count else 0.0

    predicted_insufficient = [
        r for r in results if r.predicted_outcome == "insufficient_evidence"
    ]
    expected_insufficient = [
        r for r in results if r.expected_outcome == "insufficient_evidence"
    ]
    true_positive_insufficient = sum(
        1
        for r in predicted_insufficient
        if r.expected_outcome == "insufficient_evidence"
    )
    insufficient_precision = (
        true_positive_insufficient / len(predicted_insufficient)
        if predicted_insufficient
        else None
    )
    insufficient_recall = (
        true_positive_insufficient / len(expected_insufficient)
        if expected_insufficient
        else None
    )

    answered_cases = [r for r in results if r.expected_outcome == "answered"]
    citation_checked = [r for r in answered_cases if r.citation_valid is not None]
    citation_validity_rate = (
        sum(1 for r in citation_checked if r.citation_valid) / len(citation_checked)
        if citation_checked
        else 0.0
    )
    unsupported_or_invalid_citation_rate = (
        sum(1 for r in citation_checked if not r.citation_valid) / len(citation_checked)
        if citation_checked
        else 0.0
    )

    return GroundedQaEvalReport(
        dataset_version=dataset.version,
        embedding_provider=embedding_provider_name,
        embedding_model=embedding_model,
        sample_count=sample_count,
        status_accuracy=status_accuracy,
        insufficient_precision=insufficient_precision,
        insufficient_recall=insufficient_recall,
        citation_validity_rate=citation_validity_rate,
        grounded_success_rate=(
            sum(1 for r in results if r.grounded_success) / sample_count
            if sample_count
            else 0.0
        ),
        unsupported_or_invalid_citation_rate=unsupported_or_invalid_citation_rate,
        retrieval_miss_count=sum(
            1 for r in results if r.failure_kind == "retrieval_miss"
        ),
        citation_validation_failure_count=sum(
            1 for r in results if r.failure_kind == "citation_validation"
        ),
        avg_latency_ms=(
            sum(r.latency_ms for r in results) / sample_count if sample_count else 0.0
        ),
        recall_at=retrieval_report.recall_at,
        mrr=retrieval_report.mrr,
        results=tuple(results),
    )
