"""Expected parsing failures, decoupled from PyMuPDF exception types."""


class DocumentParseError(Exception):
    """Base class for expected, safe-to-report PDF parsing failures."""


class MalformedDocumentError(DocumentParseError):
    """The file is not a valid, readable PDF."""


class EncryptedDocumentError(DocumentParseError):
    """The PDF is password-protected or otherwise encrypted."""


class PageLimitExceededError(DocumentParseError):
    """The PDF has more physical pages than the configured limit."""

    def __init__(self, page_count: int, max_pages: int) -> None:
        super().__init__(
            f"Document has {page_count} pages, exceeding the limit of {max_pages}."
        )
        self.page_count = page_count
        self.max_pages = max_pages
