"""FastAPI application entry point.

Import path for an ASGI server: ``app.main:app``.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.classification import router as classification_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.db.session import dispose_engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_engine()


app = FastAPI(title="DocuLens API", lifespan=lifespan)
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(classification_router)
