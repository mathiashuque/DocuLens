"""Reproducible retrieval baseline evaluator.

Loads a versioned dataset of small synthetic documents and labeled queries,
chunks and embeds every document with a deterministic embedding provider
(the fake adapter by default; CI never constructs a real provider), searches
each query against only its own document (mirroring the API's document
scoping), and reports Recall@K, MRR, latency, failures, chunk-size
distribution, embedding call/input counts, provenance validity, and
cross-document isolation.

`evaluate_retrieval` never calls a network or database; it operates purely
on in-memory `Chunk`/vector data built by `index_dataset_documents`, which
itself only depends on `retrieval.chunking` and an injected
`EmbeddingProvider`. A real-provider run is a separate, explicit, opt-in
script (out of scope for this baseline) that would call `index_dataset_documents`
with a real adapter and report its own cost/latency, never silently
replacing this deterministic baseline.
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from ingestion.models import DocumentPage
from retrieval.chunking import Chunk, ChunkingConfig, SectionInput, chunk_document
from retrieval.embedding import EmbeddingProvider

DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parent / "datasets" / "retrieval_v1.json"
)


class InvalidDatasetError(Exception):
    """The dataset is malformed: duplicate IDs, an unknown document
    reference, or an out-of-range labeled page."""


@dataclass(frozen=True)
class RetrievalEvalDatasetDocument:
    document_id: str
    document_type: str
    pages: list[DocumentPage]
    sections: list[SectionInput]


@dataclass(frozen=True)
class RetrievalEvalDatasetQuery:
    query_id: str
    document_id: str
    query: str
    expected_pages: tuple[int, ...]
    category: str

    @property
    def expects_no_relevant_chunk(self) -> bool:
        return len(self.expected_pages) == 0


@dataclass(frozen=True)
class RetrievalEvalDataset:
    version: str
    chunking_config: ChunkingConfig
    documents: list[RetrievalEvalDatasetDocument]
    queries: list[RetrievalEvalDatasetQuery]


def load_retrieval_dataset(path: Path = DEFAULT_DATASET_PATH) -> RetrievalEvalDataset:
    raw = json.loads(path.read_text())

    documents: list[RetrievalEvalDatasetDocument] = []
    seen_document_ids: set[str] = set()
    for raw_document in raw["documents"]:
        document_id = raw_document["document_id"]
        if document_id in seen_document_ids:
            raise InvalidDatasetError(f"duplicate document_id: {document_id}")
        seen_document_ids.add(document_id)
        pages = [
            DocumentPage(page_number=p["page_number"], text=p["text"])
            for p in raw_document["pages"]
        ]
        sections = [
            SectionInput(
                id=uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}:{s['title']}"),
                title=s["title"],
                page_start=s["page_start"],
                page_end=s["page_end"],
                section_path=s["section_path"],
                level=s["level"],
            )
            for s in raw_document.get("sections", [])
        ]
        documents.append(
            RetrievalEvalDatasetDocument(
                document_id=document_id,
                document_type=raw_document["document_type"],
                pages=pages,
                sections=sections,
            )
        )

    queries: list[RetrievalEvalDatasetQuery] = []
    seen_query_ids: set[str] = set()
    for raw_query in raw["queries"]:
        query_id = raw_query["query_id"]
        if query_id in seen_query_ids:
            raise InvalidDatasetError(f"duplicate query_id: {query_id}")
        seen_query_ids.add(query_id)
        if raw_query["document_id"] not in seen_document_ids:
            raise InvalidDatasetError(
                f"{query_id} references unknown document_id "
                f"{raw_query['document_id']!r}"
            )
        queries.append(
            RetrievalEvalDatasetQuery(
                query_id=query_id,
                document_id=raw_query["document_id"],
                query=raw_query["query"],
                expected_pages=tuple(raw_query["expected_pages"]),
                category=raw_query["category"],
            )
        )

    chunking_raw = raw.get("chunking_config", {})
    chunking_config = ChunkingConfig(
        target_tokens=chunking_raw.get("target_tokens", 800),
        overlap_tokens=chunking_raw.get("overlap_tokens", 120),
    )

    return RetrievalEvalDataset(
        version=raw["version"],
        chunking_config=chunking_config,
        documents=documents,
        queries=queries,
    )


@dataclass(frozen=True)
class IndexedDocument:
    document_id: str
    chunks: list[Chunk]
    vectors: list[list[float]]
    page_numbers: frozenset[int]
    section_ids: frozenset[uuid.UUID]


@dataclass
class IndexingStats:
    embed_document_calls: int = 0
    embedded_chunk_count: int = 0
    total_input_tokens: int = 0
    total_latency_ms: int = 0
    failed_document_ids: list[str] = field(default_factory=list)


async def index_dataset_documents(
    dataset: RetrievalEvalDataset, provider: EmbeddingProvider
) -> tuple[dict[str, IndexedDocument], IndexingStats]:
    """Chunk and embed every dataset document. Never touches a database."""
    indexed: dict[str, IndexedDocument] = {}
    stats = IndexingStats()

    for document in dataset.documents:
        try:
            chunks = chunk_document(
                document_id=uuid.uuid5(uuid.NAMESPACE_URL, document.document_id),
                pages=document.pages,
                sections=document.sections,
                config=dataset.chunking_config,
            )
        except Exception:  # noqa: BLE001 - recorded as a failed index, not raised
            stats.failed_document_ids.append(document.document_id)
            continue

        start = time.perf_counter()
        batch = await provider.embed_documents([c.text for c in chunks])
        stats.total_latency_ms += int((time.perf_counter() - start) * 1000)
        stats.embed_document_calls += 1
        stats.embedded_chunk_count += len(chunks)
        stats.total_input_tokens += batch.input_tokens or 0

        indexed[document.document_id] = IndexedDocument(
            document_id=document.document_id,
            chunks=chunks,
            vectors=batch.vectors,
            page_numbers=frozenset(p.page_number for p in document.pages),
            section_ids=frozenset(s.id for s in document.sections),
        )

    return indexed, stats


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass(frozen=True)
class RankedResult:
    chunk: Chunk
    score: float


def search_indexed_document(
    indexed: IndexedDocument, query_vector: list[float], top_k: int
) -> list[RankedResult]:
    scored = [
        RankedResult(chunk=chunk, score=_cosine(query_vector, vector))
        for chunk, vector in zip(indexed.chunks, indexed.vectors, strict=True)
    ]
    scored.sort(key=lambda r: (-r.score, r.chunk.chunk_index))
    return scored[:top_k]


@dataclass(frozen=True)
class QueryEvalResult:
    query_id: str
    category: str
    expects_no_relevant_chunk: bool
    reciprocal_rank: float | None  # None only for no-relevant-chunk queries
    hit_at: dict[int, bool]
    top_score: float | None
    latency_ms: int
    failed: bool
    leaked_cross_document: bool
    provenance_valid: bool


@dataclass(frozen=True)
class RetrievalEvalReport:
    dataset_version: str
    chunker_version: str
    chunking_config: str
    embedding_provider: str
    embedding_model: str
    dimension: int
    sample_count: int
    scored_sample_count: int
    no_relevant_query_count: int
    recall_at: dict[int, float]
    mrr: float
    failure_count: int
    chunk_count: int
    chunk_token_sizes: list[int]
    embed_document_calls: int
    embed_query_calls: int
    total_input_tokens: int
    indexing_latency_ms: int
    avg_query_latency_ms: float
    provenance_valid_count: int
    provenance_invalid_count: int
    cross_document_leakage_count: int
    no_relevant_query_top_scores: dict[str, float | None]
    failures: tuple[str, ...] = field(default_factory=tuple)


K_VALUES = (1, 3, 5)


async def evaluate_retrieval(
    dataset: RetrievalEvalDataset,
    provider: EmbeddingProvider,
    *,
    embedding_provider_name: str,
    embedding_model: str,
    dimension: int,
) -> RetrievalEvalReport:
    """Run the full baseline: index every document, run every query against
    only its own document, and score against labeled pages.

    No-relevant-chunk queries are excluded from Recall@K/MRR (there is no
    calibrated insufficiency threshold yet) and reported separately via
    `no_relevant_query_top_scores`, per the product brief's explicit
    instruction not to invent an uncalibrated threshold.
    """
    from retrieval.chunking import CHUNKER_VERSION

    indexed, indexing_stats = await index_dataset_documents(dataset, provider)

    query_results: list[QueryEvalResult] = []
    embed_query_calls = 0
    for query in dataset.queries:
        document = indexed.get(query.document_id)
        if document is None:
            query_results.append(
                QueryEvalResult(
                    query_id=query.query_id,
                    category=query.category,
                    expects_no_relevant_chunk=query.expects_no_relevant_chunk,
                    reciprocal_rank=None,
                    hit_at={},
                    top_score=None,
                    latency_ms=0,
                    failed=True,
                    leaked_cross_document=False,
                    provenance_valid=False,
                )
            )
            continue

        start = time.perf_counter()
        embedded_query = await provider.embed_query(query.query)
        embed_query_calls += 1
        results = search_indexed_document(document, embedded_query.vector, top_k=5)
        latency_ms = int((time.perf_counter() - start) * 1000)

        leaked = any(
            r.chunk.document_id != uuid.uuid5(uuid.NAMESPACE_URL, query.document_id)
            for r in results
        )
        provenance_valid = all(
            r.chunk.page_start <= r.chunk.page_end
            and r.chunk.page_start in document.page_numbers
            and r.chunk.page_end in document.page_numbers
            and (
                r.chunk.section_id is None or r.chunk.section_id in document.section_ids
            )
            for r in results
        )

        expected = set(query.expected_pages)
        rank = next(
            (
                i + 1
                for i, r in enumerate(results)
                if {r.chunk.page_start, r.chunk.page_end} & expected
                or set(range(r.chunk.page_start, r.chunk.page_end + 1)) & expected
            ),
            None,
        )
        reciprocal_rank = (
            (1.0 / rank)
            if (rank and not query.expects_no_relevant_chunk)
            else (None if query.expects_no_relevant_chunk else 0.0)
        )
        hit_at = {
            k: (rank is not None and rank <= k)
            if not query.expects_no_relevant_chunk
            else False
            for k in K_VALUES
        }

        query_results.append(
            QueryEvalResult(
                query_id=query.query_id,
                category=query.category,
                expects_no_relevant_chunk=query.expects_no_relevant_chunk,
                reciprocal_rank=reciprocal_rank,
                hit_at=hit_at,
                top_score=results[0].score if results else None,
                latency_ms=latency_ms,
                failed=False,
                leaked_cross_document=leaked,
                provenance_valid=provenance_valid,
            )
        )

    scored = [
        r for r in query_results if not r.failed and not r.expects_no_relevant_chunk
    ]
    no_relevant = [r for r in query_results if r.expects_no_relevant_chunk]
    failures = tuple(r.query_id for r in query_results if r.failed)
    failures += tuple(
        f"index:{doc_id}" for doc_id in indexing_stats.failed_document_ids
    )

    recall_at = {
        k: (
            sum(1 for r in scored if r.hit_at.get(k, False)) / len(scored)
            if scored
            else 0.0
        )
        for k in K_VALUES
    }
    mrr = sum(r.reciprocal_rank or 0.0 for r in scored) / len(scored) if scored else 0.0

    chunk_token_sizes = [
        c.token_estimate for doc in indexed.values() for c in doc.chunks
    ]

    return RetrievalEvalReport(
        dataset_version=dataset.version,
        chunker_version=CHUNKER_VERSION,
        chunking_config=dataset.chunking_config.config_id,
        embedding_provider=embedding_provider_name,
        embedding_model=embedding_model,
        dimension=dimension,
        sample_count=len(dataset.queries),
        scored_sample_count=len(scored),
        no_relevant_query_count=len(no_relevant),
        recall_at=recall_at,
        mrr=mrr,
        failure_count=len(failures),
        chunk_count=len(chunk_token_sizes),
        chunk_token_sizes=chunk_token_sizes,
        embed_document_calls=indexing_stats.embed_document_calls,
        embed_query_calls=embed_query_calls,
        total_input_tokens=indexing_stats.total_input_tokens,
        indexing_latency_ms=indexing_stats.total_latency_ms,
        avg_query_latency_ms=(
            sum(r.latency_ms for r in query_results) / len(query_results)
            if query_results
            else 0.0
        ),
        provenance_valid_count=sum(1 for r in query_results if r.provenance_valid),
        provenance_invalid_count=sum(
            1 for r in query_results if not r.provenance_valid and not r.failed
        ),
        cross_document_leakage_count=sum(
            1 for r in query_results if r.leaked_cross_document
        ),
        no_relevant_query_top_scores={r.query_id: r.top_score for r in no_relevant},
        failures=failures,
    )
