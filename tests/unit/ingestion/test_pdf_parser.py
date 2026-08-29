"""Deterministic tests for page-preserving PDF parsing."""

import pymupdf
import pytest

from ingestion.errors import (
    EncryptedDocumentError,
    MalformedDocumentError,
    PageLimitExceededError,
)
from ingestion.pdf_parser import has_pdf_signature, parse_pdf


def _build_pdf(pages_text: list[str]) -> bytes:
    document = pymupdf.open()
    for text in pages_text:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


def _build_encrypted_pdf() -> bytes:
    document = pymupdf.open()
    document.new_page()
    data = document.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user"
    )
    document.close()
    return data


def test_two_page_text_pdf_maps_pages_one_based() -> None:
    data = _build_pdf(["First page text", "Second page text"])

    result = parse_pdf(data, max_pages=40)

    assert result.status == "parsed"
    assert result.page_count == 2
    assert [page.page_number for page in result.pages] == [1, 2]
    assert "First page text" in result.pages[0].text
    assert "Second page text" in result.pages[1].text
    assert "First page text" not in result.pages[1].text
    assert "Second page text" not in result.pages[0].text


def test_blank_physical_page_is_preserved_without_collapsing_numbers() -> None:
    data = _build_pdf(["Some text", ""])

    result = parse_pdf(data, max_pages=40)

    assert result.page_count == 2
    assert result.pages[0].page_number == 1
    assert result.pages[1].page_number == 2
    assert result.pages[1].text == ""


def test_no_text_pdf_requires_ocr() -> None:
    data = _build_pdf(["", ""])

    result = parse_pdf(data, max_pages=40)

    assert result.status == "ocr_required"
    assert result.page_count == 2


def test_malformed_input_raises_malformed_document_error() -> None:
    with pytest.raises(MalformedDocumentError):
        parse_pdf(b"not a pdf at all", max_pages=40)


def test_encrypted_pdf_raises_encrypted_document_error() -> None:
    data = _build_encrypted_pdf()

    with pytest.raises(EncryptedDocumentError):
        parse_pdf(data, max_pages=40)


def test_page_limit_is_enforced() -> None:
    data = _build_pdf(["one", "two", "three"])

    with pytest.raises(PageLimitExceededError) as excinfo:
        parse_pdf(data, max_pages=2)

    assert excinfo.value.page_count == 3
    assert excinfo.value.max_pages == 2


def test_has_pdf_signature() -> None:
    assert has_pdf_signature(b"%PDF-1.4 rest")
    assert not has_pdf_signature(b"not a pdf")
