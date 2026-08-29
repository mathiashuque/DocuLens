"""Deterministic, page-aware section detection.

Pure heuristic boundary: accepts ordered `DocumentPage` values and returns
typed section candidates with no HTTP, ORM, database, provider, or global
state dependencies. Prefers no detected section over a confident-looking
false hierarchy.
"""

import re

from pydantic import BaseModel

from ingestion.models import DocumentPage

_NUMBERED_HEADING_RE = re.compile(r"^(\d+(?:\.\d+){0,5})[.)]?\s+(\S.*)$")
_UPPERCASE_HEADING_RE = re.compile(r"^[A-Z0-9][A-Z0-9 &\-/,.'()]*$")

_MAX_NUMBERED_TITLE_WORDS = 12
_MAX_NUMBERED_TITLE_CHARS = 100
_MAX_UPPERCASE_HEADING_WORDS = 6
_MAX_UPPERCASE_HEADING_CHARS = 60


class SectionCandidate(BaseModel):
    """A detected section, addressable by its position in the returned list."""

    title: str
    level: int
    parent_index: int | None
    page_start: int
    page_end: int
    section_path: list[str]
    text: str


class _Line(BaseModel):
    page_number: int
    text: str


def _iter_lines(pages: list[DocumentPage]) -> list[_Line]:
    return [
        _Line(page_number=page.page_number, text=line)
        for page in pages
        for line in page.text.split("\n")
    ]


def _match_numbered_heading(line: str) -> tuple[int, str] | None:
    match = _NUMBERED_HEADING_RE.match(line)
    if not match:
        return None
    numeric_prefix, title = match.group(1), match.group(2).strip()
    if not title or title.isdigit():
        return None
    if len(title) > _MAX_NUMBERED_TITLE_CHARS:
        return None
    if len(title.split()) > _MAX_NUMBERED_TITLE_WORDS:
        return None
    level = numeric_prefix.count(".") + 1
    return level, line.strip()


def _match_uppercase_heading(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None
    if len(stripped) > _MAX_UPPERCASE_HEADING_CHARS:
        return None
    if len(stripped.split()) > _MAX_UPPERCASE_HEADING_WORDS:
        return None
    if not any(char.isalpha() for char in stripped):
        return None
    if not _UPPERCASE_HEADING_RE.match(stripped):
        return None
    return stripped


def _detect_headings(lines: list[_Line]) -> list[tuple[int, int, str, int]]:
    """Returns (line_index, page_number, title, level) for each heading line."""
    headings: list[tuple[int, int, str, int]] = []
    for index, line in enumerate(lines):
        text = line.text.strip()
        if not text:
            continue
        numbered = _match_numbered_heading(text)
        if numbered is not None:
            level, title = numbered
            headings.append((index, line.page_number, title, level))
            continue
        uppercase_title = _match_uppercase_heading(text)
        if uppercase_title is not None:
            headings.append((index, line.page_number, uppercase_title, 1))
    return headings


def detect_sections(pages: list[DocumentPage]) -> list[SectionCandidate]:
    """Detect conservative structural sections from ordered page text.

    Returns an empty list when no supported heading is found, including for
    all-empty page text (e.g. `ocr_required` documents).
    """
    if not any(page.text.strip() for page in pages):
        return []

    lines = _iter_lines(pages)
    headings = _detect_headings(lines)
    if not headings:
        return []

    candidates: list[SectionCandidate] = []
    stack: list[tuple[int, int]] = []  # (level, candidate_index)

    for position, (line_index, page_number, title, level) in enumerate(headings):
        while stack and stack[-1][0] >= level:
            stack.pop()
        parent_index = stack[-1][1] if stack else None
        parent_path = (
            candidates[parent_index].section_path if parent_index is not None else []
        )
        section_path = [*parent_path, title]

        end_line_index = (
            headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        )
        span_lines = lines[line_index:end_line_index]
        text = "\n".join(line.text for line in span_lines).strip()
        page_end = max(line.page_number for line in span_lines)

        candidates.append(
            SectionCandidate(
                title=title,
                level=level,
                parent_index=parent_index,
                page_start=page_number,
                page_end=page_end,
                section_path=section_path,
                text=text,
            )
        )
        stack.append((level, len(candidates) - 1))

    return candidates
