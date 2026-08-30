"""Unit tests for upload/parse/hash/persist orchestration, using fakes for the
persistence boundary so no database is required.
"""

import io
import uuid
from typing import Any

import pytest
from app.core.config import UploadSettings
from app.services.document_persistence import (
    DocumentNotFoundError,
    create_document,
    get_document,
)
from starlette.datastructures import UploadFile

UPLOAD_SETTINGS = UploadSettings()


class _RaisingSession:
    """Fails if the orchestration touches the session after an upload error."""


class _FakeCreatedDocument:
    def __init__(self) -> None:
        self.id = uuid.uuid4()


class _RecordingRepository:
    def __init__(self, _session: Any) -> None:
        self.create_calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> _FakeCreatedDocument:
        self.create_calls.append(kwargs)
        return _FakeCreatedDocument()

    async def get(self, document_id: uuid.UUID) -> None:
        return None


@pytest.mark.asyncio
async def test_create_document_propagates_upload_errors_without_persisting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_instances: list[_RecordingRepository] = []

    def _tracking_repository(session: Any) -> _RecordingRepository:
        repo = _RecordingRepository(session)
        repository_instances.append(repo)
        return repo

    monkeypatch.setattr(
        "app.services.document_persistence.DocumentRepository", _tracking_repository
    )

    from app.services.document_parsing import UnsupportedFileTypeError
    from starlette.datastructures import Headers

    upload = UploadFile(
        filename="bad.txt",
        file=io.BytesIO(b"not a pdf"),
        headers=Headers({"content-type": "text/plain"}),
    )

    with pytest.raises(UnsupportedFileTypeError):
        await create_document(upload, UPLOAD_SETTINGS, _RaisingSession())  # type: ignore[arg-type]

    assert repository_instances == []


@pytest.mark.asyncio
async def test_get_document_raises_not_found_when_repository_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.document_persistence.DocumentRepository", _RecordingRepository
    )

    with pytest.raises(DocumentNotFoundError):
        await get_document(uuid.uuid4(), _RaisingSession())  # type: ignore[arg-type]
