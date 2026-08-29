"""Deterministic tests for the page-aware section detector."""

from ingestion.models import DocumentPage
from ingestion.sections import detect_sections


def _pages(*texts: str) -> list[DocumentPage]:
    return [
        DocumentPage(page_number=index + 1, text=text)
        for index, text in enumerate(texts)
    ]


def test_numbered_hierarchy_levels_one_two_three() -> None:
    pages = _pages(
        "1 Introduction\nSome intro text.\n"
        "1.1 Background\nBackground text.\n"
        "1.1.1 Origins\nOrigins text."
    )

    sections = detect_sections(pages)

    assert [(s.title, s.level) for s in sections] == [
        ("1 Introduction", 1),
        ("1.1 Background", 2),
        ("1.1.1 Origins", 3),
    ]
    assert sections[0].parent_index is None
    assert sections[1].parent_index == 0
    assert sections[2].parent_index == 1
    assert sections[2].section_path == [
        "1 Introduction",
        "1.1 Background",
        "1.1.1 Origins",
    ]


def test_same_level_transition_and_return_to_top_level() -> None:
    pages = _pages("1 First\nbody\n2 Second\nbody\n2.1 Child\nbody\n3 Third\nbody")

    sections = detect_sections(pages)

    titles_and_parents = [(s.title, s.parent_index) for s in sections]
    assert titles_and_parents == [
        ("1 First", None),
        ("2 Second", None),
        ("2.1 Child", 1),
        ("3 Third", None),
    ]


def test_skipped_numeric_level_attaches_to_nearest_lower_level_without_fabrication() -> (
    None
):
    pages = _pages("1 Top\nbody\n1.2.1 Deep\nbody")

    sections = detect_sections(pages)

    assert len(sections) == 2
    assert sections[1].title == "1.2.1 Deep"
    assert sections[1].level == 3
    assert sections[1].parent_index == 0
    assert sections[1].section_path == ["1 Top", "1.2.1 Deep"]


def test_supported_uppercase_top_level_heading() -> None:
    pages = _pages("TERMINATION\nThis agreement may be terminated.")

    sections = detect_sections(pages)

    assert len(sections) == 1
    assert sections[0].title == "TERMINATION"
    assert sections[0].level == 1
    assert sections[0].parent_index is None


def test_rejects_prose_numeric_only_and_punctuation_lines() -> None:
    pages = _pages(
        "This is a normal paragraph of prose text that happens to be long.\n"
        "3.14\n"
        "----\n"
        "Page 3\n"
        "12345"
    )

    sections = detect_sections(pages)

    assert sections == []


def test_rejects_overly_long_uppercase_line() -> None:
    long_uppercase = " ".join(["WORD"] * 20)
    pages = _pages(long_uppercase)

    sections = detect_sections(pages)

    assert sections == []


def test_content_spans_multiple_physical_pages_with_accurate_page_range() -> None:
    pages = _pages(
        "1 Introduction\nPage one body.",
        "still part of section one",
        "2 Next\nsecond section body",
    )

    sections = detect_sections(pages)

    assert sections[0].page_start == 1
    assert sections[0].page_end == 2
    assert sections[1].page_start == 3
    assert sections[1].page_end == 3


def test_consecutive_headings_produce_empty_section_body() -> None:
    pages = _pages("1 First\n2 Second\nbody text")

    sections = detect_sections(pages)

    assert sections[0].text == "1 First"
    assert sections[1].text == "2 Second\nbody text"


def test_blank_physical_page_does_not_shift_numbering() -> None:
    pages = _pages("1 Introduction\nbody", "", "2 Next\nbody")

    sections = detect_sections(pages)

    assert sections[0].page_start == 1
    assert sections[0].page_end == 2
    assert sections[1].page_start == 3


def test_preamble_before_first_heading_is_excluded_from_sections() -> None:
    pages = _pages("Preamble text with no heading.\n1 Introduction\nbody")

    sections = detect_sections(pages)

    assert len(sections) == 1
    assert "Preamble" not in sections[0].text
    assert sections[0].title == "1 Introduction"


def test_no_headings_returns_empty_list() -> None:
    pages = _pages("Just some prose with no structure at all.")

    assert detect_sections(pages) == []


def test_all_empty_pages_returns_empty_list() -> None:
    pages = _pages("", "")

    assert detect_sections(pages) == []


def test_sections_have_non_overlapping_exact_source_derived_text() -> None:
    pages = _pages("1 First\nfirst body\n2 Second\nsecond body")

    sections = detect_sections(pages)

    assert sections[0].text == "1 First\nfirst body"
    assert sections[1].text == "2 Second\nsecond body"
    assert "second body" not in sections[0].text
    assert "first body" not in sections[1].text
