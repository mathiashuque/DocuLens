"""Upload validation limits, sourced from environment configuration."""

import os
from dataclasses import dataclass


class InvalidConfigurationError(Exception):
    """An environment-configured value is invalid."""


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise InvalidConfigurationError(f"{name} must be an integer.") from exc
    if value <= 0:
        raise InvalidConfigurationError(f"{name} must be a positive integer.")
    return value


@dataclass(frozen=True)
class UploadSettings:
    max_upload_mb: int = 10
    max_document_pages: int = 40

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


def load_upload_settings() -> UploadSettings:
    return UploadSettings(
        max_upload_mb=_positive_int("MAX_UPLOAD_MB", 10),
        max_document_pages=_positive_int("MAX_DOCUMENT_PAGES", 40),
    )
