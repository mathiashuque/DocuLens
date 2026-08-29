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
class ClassificationSettings:
    """Classification provider/model/threshold configuration.

    Read lazily at the classification boundary only; never at app import,
    `/health`, or GET classification, so a missing key never breaks
    unrelated requests.
    """

    api_key: str | None
    model: str
    confidence_threshold: float
    timeout_seconds: float
    max_output_tokens: int


DEFAULT_CLASSIFICATION_MODEL = "gpt-4o-mini"
DEFAULT_CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.65
DEFAULT_CLASSIFICATION_TIMEOUT_SECONDS = 30.0
DEFAULT_CLASSIFICATION_MAX_OUTPUT_TOKENS = 800


def _float_in_unit_interval(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise InvalidConfigurationError(f"{name} must be a number.") from exc
    if not 0.0 <= value <= 1.0:
        raise InvalidConfigurationError(f"{name} must be within [0, 1].")
    return value


def load_classification_settings() -> ClassificationSettings:
    return ClassificationSettings(
        api_key=os.environ.get("OPENAI_API_KEY") or None,
        model=os.environ.get("CLASSIFICATION_MODEL", DEFAULT_CLASSIFICATION_MODEL),
        confidence_threshold=_float_in_unit_interval(
            "CLASSIFICATION_CONFIDENCE_THRESHOLD",
            DEFAULT_CLASSIFICATION_CONFIDENCE_THRESHOLD,
        ),
        timeout_seconds=DEFAULT_CLASSIFICATION_TIMEOUT_SECONDS,
        max_output_tokens=DEFAULT_CLASSIFICATION_MAX_OUTPUT_TOKENS,
    )


@dataclass(frozen=True)
class AnalysisSettings:
    """Generic analysis provider/model/context configuration.

    Read lazily at the analysis boundary only; never at app import,
    `/health`, or GET analysis.
    """

    api_key: str | None
    model: str
    timeout_seconds: float
    max_output_tokens: int
    budget_chars: int


DEFAULT_ANALYSIS_MODEL = "gpt-4o-mini"
DEFAULT_ANALYSIS_TIMEOUT_SECONDS = 60.0
DEFAULT_ANALYSIS_MAX_OUTPUT_TOKENS = 2000
DEFAULT_ANALYSIS_BUDGET_CHARS = 12000


def load_analysis_settings() -> AnalysisSettings:
    return AnalysisSettings(
        api_key=os.environ.get("OPENAI_API_KEY") or None,
        model=os.environ.get("ANALYSIS_MODEL", DEFAULT_ANALYSIS_MODEL),
        timeout_seconds=DEFAULT_ANALYSIS_TIMEOUT_SECONDS,
        max_output_tokens=DEFAULT_ANALYSIS_MAX_OUTPUT_TOKENS,
        budget_chars=_positive_int(
            "ANALYSIS_BUDGET_CHARS", DEFAULT_ANALYSIS_BUDGET_CHARS
        ),
    )


@dataclass(frozen=True)
class EmbeddingSettings:
    """Embedding provider/model/dimension/batch configuration for indexing
    and search.

    Read lazily at the retrieval boundary only (index/search services);
    never at app import, `/health`, upload, or analysis, so a missing key
    never breaks unrelated requests. `dimension` must match both the
    configured model's actual output and the `document_chunks.embedding`
    column defined in the retrieval migration; changing it requires a new
    migration and an explicit reindex, never a silent runtime change.
    """

    api_key: str | None
    model: str
    dimension: int
    timeout_seconds: float
    max_batch_size: int
    max_query_chars: int
    max_top_k: int


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_DIMENSION = 1536
DEFAULT_EMBEDDING_TIMEOUT_SECONDS = 30.0
DEFAULT_EMBEDDING_MAX_BATCH_SIZE = 96
DEFAULT_EMBEDDING_MAX_QUERY_CHARS = 2000
DEFAULT_EMBEDDING_MAX_TOP_K = 20


def load_embedding_settings() -> EmbeddingSettings:
    return EmbeddingSettings(
        api_key=os.environ.get("OPENAI_API_KEY") or None,
        model=os.environ.get("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        dimension=_positive_int("EMBEDDING_DIMENSION", DEFAULT_EMBEDDING_DIMENSION),
        timeout_seconds=DEFAULT_EMBEDDING_TIMEOUT_SECONDS,
        max_batch_size=_positive_int(
            "EMBEDDING_MAX_BATCH_SIZE", DEFAULT_EMBEDDING_MAX_BATCH_SIZE
        ),
        max_query_chars=_positive_int(
            "EMBEDDING_MAX_QUERY_CHARS", DEFAULT_EMBEDDING_MAX_QUERY_CHARS
        ),
        max_top_k=_positive_int("EMBEDDING_MAX_TOP_K", DEFAULT_EMBEDDING_MAX_TOP_K),
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
