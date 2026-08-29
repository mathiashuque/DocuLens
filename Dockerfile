# DocuLens API image.
#
# Build context is the repository root because `apps/api/app` imports the
# root-level `ingestion` package. Only the packages the API actually uses are
# copied in; see `.dockerignore` for what is excluded.

FROM python:3.12.7-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/code

WORKDIR /code

# Install dependencies first so source-only changes reuse the layer cache.
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/api/app apps/api/app
RUN pip install --no-cache-dir ./apps/api

# Root-level packages imported by the API, kept separate from the installed
# `app` package so PYTHONPATH resolves them without a second install step.
COPY ingestion ingestion

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /code
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
