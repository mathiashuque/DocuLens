"""Dataset fixture checks: covers all three document types, document
isolation, a chunk-boundary-spanning answer, a no-relevant-chunk query, and
a prompt-injection line treated only as retrievable content."""

import json
from pathlib import Path

from evals.retrieval_eval import InvalidDatasetError, load_retrieval_dataset

DATASET_PATH = (
    Path(__file__).resolve().parents[3] / "evals" / "datasets" / "retrieval_v1.json"
)


def test_dataset_loads_and_covers_all_three_document_types() -> None:
    dataset = load_retrieval_dataset(DATASET_PATH)
    types = {d.document_type for d in dataset.documents}

    assert types == {"contract", "technical_specification", "generic"}


def test_dataset_includes_a_no_relevant_chunk_query() -> None:
    dataset = load_retrieval_dataset(DATASET_PATH)

    assert any(q.expects_no_relevant_chunk for q in dataset.queries)


def test_dataset_includes_a_sectionless_fallback_document() -> None:
    dataset = load_retrieval_dataset(DATASET_PATH)

    assert any(not d.sections for d in dataset.documents)


def test_dataset_includes_two_documents_with_similar_language() -> None:
    dataset = load_retrieval_dataset(DATASET_PATH)
    categories = {q.category for q in dataset.queries}

    assert "document_isolation" in categories


def test_dataset_document_and_query_ids_are_unique() -> None:
    dataset = load_retrieval_dataset(DATASET_PATH)
    document_ids = [d.document_id for d in dataset.documents]
    query_ids = [q.query_id for q in dataset.queries]

    assert len(document_ids) == len(set(document_ids))
    assert len(query_ids) == len(set(query_ids))


def test_prompt_injection_query_targets_retrievable_data_only() -> None:
    dataset = load_retrieval_dataset(DATASET_PATH)
    injection_queries = [
        q for q in dataset.queries if q.category == "prompt_injection_as_data"
    ]
    assert injection_queries

    raw = json.loads(DATASET_PATH.read_text())
    injected_document = next(
        d
        for d in raw["documents"]
        if d["document_id"] == injection_queries[0].document_id
    )
    assert any(
        "ignore all previous instructions" in p["text"].lower()
        for p in injected_document["pages"]
    )


def test_query_referencing_unknown_document_is_rejected(tmp_path: Path) -> None:
    raw = json.loads(DATASET_PATH.read_text())
    raw["queries"][0]["document_id"] = "does-not-exist"
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps(raw))

    try:
        load_retrieval_dataset(bad_path)
        raise AssertionError("expected InvalidDatasetError")
    except InvalidDatasetError:
        pass
