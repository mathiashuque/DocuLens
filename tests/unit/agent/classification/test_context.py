"""Context selection unit tests: budget, page labels, stable sampling,
blank-page handling, short/long documents, and no duplicated excerpts."""

from agent.classification.context import (
    MAX_PAGE_SAMPLES,
    select_classification_context,
)


def test_short_document_retains_full_beginning_within_budget() -> None:
    pages = [(1, "Short opening paragraph.")]

    context = select_classification_context(
        filename="doc.pdf", pages=pages, section_titles=[]
    )

    assert len(context.excerpts) == 1
    assert context.excerpts[0].page == 1
    assert context.excerpts[0].text == "Short opening paragraph."
    assert context.truncated is False


def test_blank_pages_contribute_no_excerpt() -> None:
    pages = [(1, "Real content."), (2, "   "), (3, "")]

    context = select_classification_context(
        filename="doc.pdf", pages=pages, section_titles=[]
    )

    assert [excerpt.page for excerpt in context.excerpts] == [1]


def test_long_document_includes_beginning_plus_spread_samples() -> None:
    pages = [(number, f"Page {number} body text.") for number in range(1, 51)]

    context = select_classification_context(
        filename="doc.pdf", pages=pages, section_titles=[]
    )

    pages_selected = [excerpt.page for excerpt in context.excerpts]
    assert pages_selected[0] == 1
    assert len(pages_selected) <= MAX_PAGE_SAMPLES
    assert len(pages_selected) > 1
    assert pages_selected == sorted(pages_selected)
    assert len(set(pages_selected)) == len(pages_selected)


def test_every_excerpt_keeps_its_physical_page_number() -> None:
    pages = [(5, "five"), (9, "nine"), (12, "twelve")]

    context = select_classification_context(
        filename="doc.pdf", pages=pages, section_titles=[]
    )

    assert {excerpt.page for excerpt in context.excerpts} == {5, 9, 12}


def test_selection_is_stable_across_runs() -> None:
    pages = [(number, f"Page {number} " * 50) for number in range(1, 41)]

    first = select_classification_context(
        filename="doc.pdf", pages=pages, section_titles=["Intro"]
    )
    second = select_classification_context(
        filename="doc.pdf", pages=pages, section_titles=["Intro"]
    )

    assert first == second


def test_budget_is_enforced() -> None:
    pages = [(number, "x" * 5000) for number in range(1, 11)]

    context = select_classification_context(
        filename="doc.pdf", pages=pages, section_titles=[], budget_chars=1000
    )

    assert context.total_excerpt_chars <= 1000
    assert context.truncated is True


def test_section_titles_are_deduplicated_and_capped() -> None:
    titles = ["Intro", "Intro", "Terms"] + [f"Section {i}" for i in range(20)]

    context = select_classification_context(
        filename="doc.pdf", pages=[(1, "text")], section_titles=titles
    )

    assert context.section_titles.count("Intro") == 1
    assert len(context.section_titles) <= 15


def test_empty_document_produces_no_excerpts() -> None:
    context = select_classification_context(
        filename="doc.pdf", pages=[], section_titles=[]
    )

    assert context.excerpts == []
    assert context.truncated is False
