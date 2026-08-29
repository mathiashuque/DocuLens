"""FastAPI application entry point.

Import path for an ASGI server: ``app.main:app``.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.analysis import router as analysis_router
from app.api.classification import router as classification_router
from app.api.demos import router as demos_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.questions import router as questions_router
from app.api.retrieval import router as retrieval_router
from app.api.usage import router as usage_router
from app.db.session import dispose_engine
from app.services.quota import QuotaExceededError


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_engine()


app = FastAPI(title="DocuLens API", lifespan=lifespan)


@app.exception_handler(QuotaExceededError)
async def quota_exceeded_handler(
    _request: Request, exc: QuotaExceededError
) -> JSONResponse:
    body = {
        "error": "quota_exceeded",
        "category": exc.category,
        "limit": exc.limit,
        "remaining": 0,
        "retry_at": exc.retry_at.isoformat().replace("+00:00", "Z")
        if exc.retry_at
        else None,
    }
    headers = {}
    if exc.retry_at is not None:
        from datetime import UTC, datetime

        headers["Retry-After"] = str(
            max(0, int((exc.retry_at - datetime.now(UTC)).total_seconds()))
        )
    return JSONResponse(body, status_code=429, headers=headers)


app.include_router(health_router)
app.include_router(documents_router)
app.include_router(demos_router)
app.include_router(classification_router)
app.include_router(analysis_router)
app.include_router(retrieval_router)
app.include_router(questions_router)
app.include_router(usage_router)
