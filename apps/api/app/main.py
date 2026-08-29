"""FastAPI application entry point.

Import path for an ASGI server: ``app.main:app``.
"""

from fastapi import FastAPI

from app.api.health import router as health_router

app = FastAPI(title="DocuLens API")
app.include_router(health_router)
