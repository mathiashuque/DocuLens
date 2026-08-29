"""Dataset fixture checks: covers all three types, ambiguity, and a
prompt-injection sample; the pipeline treats that sample's text as quoted
data, never instructions."""

import json
from pathlib import Path

from agent.classification.context import select_classification_context
from agent.classification.prompt import render_user_content
from agent.classification.taxonomy import ALLOWED_DOCUMENT_TYPES

DATASET_PATH = (
    Path(__file__).resolve().parents[3]
    / "evals"
    / "datasets"
    / "classification_v1.json"
)


def _load_samples() -> list[dict[str, object]]:
    return json.loads(DATASET_PATH.read_text())["samples"]


def test_dataset_covers_all_three_types() -> None:
    samples = _load_samples()
    expected_types = {sample["expected_type"] for sample in samples}

    assert expected_types == set(ALLOWED_DOCUMENT_TYPES)


def test_dataset_includes_a_prompt_injection_sample() -> None:
    samples = _load_samples()

    assert any(sample["is_prompt_injection"] for sample in samples)


def test_dataset_sample_ids_are_unique() -> None:
    samples = _load_samples()
    ids = [sample["sample_id"] for sample in samples]

    assert len(ids) == len(set(ids))


def test_prompt_injection_sample_stays_quoted_data_through_the_pipeline() -> None:
    samples = _load_samples()
    injection_sample = next(s for s in samples if s["is_prompt_injection"])
    text = str(injection_sample["text"])

    context = select_classification_context(
        filename="notes.pdf", pages=[(1, text)], section_titles=[]
    )
    rendered = render_user_content(context)

    start = rendered.index("<document_excerpts>")
    end = rendered.index("</document_excerpts>")
    assert text in rendered[start:end]
    assert text not in rendered[:start]
    assert text not in rendered[end:]
