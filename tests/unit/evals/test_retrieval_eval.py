"""Retrieval evaluator tests: deterministic fake-provider run, metric
correctness, reproducibility, and dataset/document isolation invariants.
No test in this module makes a network call."""

import uuid

import pytest

from evals.retrieval_eval import (
    IndexedDocument,
    RetrievalEvalDataset,
    RetrievalEvalDatasetDocument,
    RetrievalEvalDatasetQuery,
    evaluate_retrieval,
    load_retrieval_dataset,
    search_indexed_document,
)
from ingestion.models import DocumentPage
from retrieval.chunking import Chunk, ChunkingConfig
from retrieval.providers.fake_provider import FakeEmbeddingProvider


@pytest.mark.asyncio
async def test_full_dataset_evaluation_is_reproducible() -> None:
    dataset = load_retrieval_dataset()
    provider = FakeEmbeddingProvider(dimension=32)

    first = await evaluate_retrieval(
        dataset,
        provider,
        embedding_provider_name="fake",
        embedding_model=provider.model,
        dimension=32,
    )
    second = await evaluate_retrieval(
        dataset,
        provider,
        embedding_provider_name="fake",
        embedding_model=provider.model,
        dimension=32,
    )

    assert first.recall_at == second.recall_at
    assert first.mrr == second.mrr
    assert first.chunk_count == second.chunk_count


@pytest.mark.asyncio
async def test_full_dataset_evaluation_reports_expected_metadata() -> None:
    dataset = load_retrieval_dataset()
    provider = FakeEmbeddingProvider(dimension=32)

    report = await evaluate_retrieval(
        dataset,
        provider,
        embedding_provider_name="fake",
        embedding_model=provider.model,
        dimension=32,
    )

    assert report.dataset_version == "retrieval_v1"
    assert report.sample_count == len(dataset.queries)
    assert report.no_relevant_query_count >= 1
    assert (
        report.scored_sample_count
        == report.sample_count - report.no_relevant_query_count
    )
    assert report.failure_count == 0
    assert report.cross_document_leakage_count == 0
    assert report.provenance_invalid_count == 0
    assert 0.0 <= report.mrr <= 1.0
    for value in report.recall_at.values():
        assert 0.0 <= value <= 1.0
    assert report.embed_document_calls == len(dataset.documents)
    assert report.embed_query_calls == len(dataset.queries)
    assert report.chunk_count == len(report.chunk_token_sizes)


def test_search_indexed_document_orders_by_score_with_stable_tie_break() -> None:
    doc_id = uuid.uuid4()
    chunks = [
        Chunk(
            id=uuid.uuid4(),
            document_id=doc_id,
            chunk_index=i,
            text=f"chunk {i}",
            page_start=1,
            page_end=1,
            section_id=None,
            section_title=None,
            section_path=[],
            token_estimate=2,
        )
        for i in range(3)
    ]
    vectors = [[1.0, 0.0], [0.0, 1.0], [0.0, 1.0]]  # chunk 1 and 2 tie
    indexed = IndexedDocument(
        document_id="doc",
        chunks=chunks,
        vectors=vectors,
        page_numbers=frozenset({1}),
        section_ids=frozenset(),
    )

    results = search_indexed_document(indexed, [0.0, 1.0], top_k=3)

    assert [r.chunk.chunk_index for r in results] == [1, 2, 0]


@pytest.mark.asyncio
async def test_no_relevant_chunk_query_is_excluded_from_recall_and_reported_separately() -> (
    None
):
    doc = RetrievalEvalDatasetDocument(
        document_id="d1",
        document_type="generic",
        pages=[DocumentPage(page_number=1, text="alpha beta gamma delta")],
        sections=[],
    )
    query = RetrievalEvalDatasetQuery(
        query_id="q1",
        document_id="d1",
        query="unrelated topic entirely",
        expected_pages=(),
        category="no_relevant_chunk",
    )
    dataset = RetrievalEvalDataset(
        version="test",
        chunking_config=ChunkingConfig(target_tokens=10, overlap_tokens=2),
        documents=[doc],
        queries=[query],
    )
    provider = FakeEmbeddingProvider(dimension=8)

    report = await evaluate_retrieval(
        dataset,
        provider,
        embedding_provider_name="fake",
        embedding_model=provider.model,
        dimension=8,
    )

    assert report.scored_sample_count == 0
    assert report.no_relevant_query_count == 1
    assert "q1" in report.no_relevant_query_top_scores
    assert report.mrr == 0.0  # no scored samples
