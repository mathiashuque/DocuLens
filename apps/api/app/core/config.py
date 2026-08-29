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


@dataclass(frozen=True)
class DatabaseSettings:
    """Canonical application database connection setting.

    Never logged or included in error responses: it carries credentials.
    """

    database_url: str


def load_database_settings() -> DatabaseSettings:
    """Read ``DATABASE_URL``, or assemble it from local Postgres variables.

    Compose sets ``DATABASE_URL`` directly from its own ``POSTGRES_*``
    substitution; assembling a fallback here keeps host-side tooling (Alembic,
    tests) working without duplicating that connection string in a second place.
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        return DatabaseSettings(database_url=url)

    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    database = os.environ.get("POSTGRES_DB", "doculens")
    user = os.environ.get("POSTGRES_USER", "doculens")
    password = os.environ.get("POSTGRES_PASSWORD", "doculens_local_only")
    return DatabaseSettings(
        database_url=f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
    )
