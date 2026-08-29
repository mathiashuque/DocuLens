"""Context selection tests: with/without section structure, stable
ordering, page labels, blank-page handling, and budget bounds."""

from agent.extractors.contract.context import SectionSpan, select_contract_context


def test_prioritizes_pages_covered_by_matching_section_titles() -> None:
    pages = [
        (1, "Title page. Parties: Northstar Hosting Ltd. and Customer Inc."),
        (2, "Scope of services description, not otherwise relevant."),
        (3, "Payment terms: Customer shall pay $1,000 monthly."),
        (4, "Miscellaneous boilerplate."),
    ]
    sections = [
        SectionSpan(title="Scope of Services", page_start=2, page_end=2),
        SectionSpan(title="Payment Terms", page_start=3, page_end=3),
    ]
    context = select_contract_context(
        filename="contract.pdf", pages=pages, sections=sections, budget_chars=6000
    )
    included_pages = {excerpt.page for excerpt in context.excerpts}
    assert 1 in included_pages  # title/intro page always included
    assert 3 in included_pages  # matched "Payment Terms" section


def test_falls_back_to_plain_sampling_when_no_sections_supplied() -> None:
    pages = [(1, "Title page."), (2, "Body text."), (3, "More body text.")]
    context = select_contract_context(
        filename="contract.pdf", pages=pages, sections=None
    )
    assert context.excerpts
    assert context.excerpts[0].page == 1


def test_falls_back_to_plain_sampling_when_no_section_matches_keywords() -> None:
    pages = [(1, "Title page."), (2, "Unrelated boilerplate section body.")]
    sections = [SectionSpan(title="Preamble", page_start=2, page_end=2)]
    context = select_contract_context(
        filename="contract.pdf", pages=pages, sections=sections
    )
    assert context.excerpts[0].page == 1


def test_ignores_blank_pages() -> None:
    pages = [(1, "Title page with content."), (2, "   "), (3, "")]
    context = select_contract_context(filename="contract.pdf", pages=pages)
    assert all(excerpt.page != 2 and excerpt.page != 3 for excerpt in context.excerpts)


def test_empty_document_returns_empty_context() -> None:
    context = select_contract_context(filename="empty.pdf", pages=[(1, "   ")])
    assert context.excerpts == []


def test_selection_is_deterministic_across_calls() -> None:
    pages = [
        (n, f"Page {n} body text about renewal and termination clauses.")
        for n in range(1, 10)
    ]
    sections = [SectionSpan(title="Renewal", page_start=5, page_end=6)]
    first = select_contract_context(filename="doc.pdf", pages=pages, sections=sections)
    second = select_contract_context(filename="doc.pdf", pages=pages, sections=sections)
    assert [e.page for e in first.excerpts] == [e.page for e in second.excerpts]


def test_respects_budget_chars() -> None:
    pages = [(1, "A" * 500), (2, "B" * 500), (3, "C" * 500)]
    context = select_contract_context(filename="doc.pdf", pages=pages, budget_chars=300)
    assert context.total_excerpt_chars <= 300
    assert context.truncated
