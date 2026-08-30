"""Tests for environment-backed core configuration."""

from app.core.config import load_database_settings


def test_database_url_takes_precedence_and_normalizes_neon_url(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://neon_user:placeholder@neon.example/doculens?sslmode=require&channel_binding=require",
    )
    monkeypatch.setenv("POSTGRES_DB", "ignored_database")
    monkeypatch.setenv("POSTGRES_USER", "ignored_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "ignored_password")

    settings = load_database_settings()

    assert settings.database_url == (
        "postgresql+asyncpg://neon_user:placeholder@neon.example/doculens?ssl=require"
    )


def test_database_url_with_asyncpg_dialect_is_unchanged(monkeypatch) -> None:
    configured_url = (
        "postgresql+asyncpg://user:password@db.example/doculens?ssl=require"
    )
    monkeypatch.setenv("DATABASE_URL", configured_url)

    assert load_database_settings().database_url == configured_url
