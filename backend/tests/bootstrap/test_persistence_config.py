"""Configuration de la persistance : choix de l'adaptateur, URL obligatoire et secrète."""

import pytest

from app.bootstrap.config import (
    ConfigurationError,
    PersistenceBackend,
    load_database_url,
    load_settings,
)

URL = "postgresql+psycopg://boutique:tres-secret@127.0.0.1:5432/boutique"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ENVIRONMENT", "PERSISTENCE_BACKEND", "DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize(
    ("environment", "expected"),
    [("test", PersistenceBackend.MEMORY), ("dev", PersistenceBackend.POSTGRES)],
)
def test_default_backend_depends_on_environment(
    monkeypatch: pytest.MonkeyPatch, environment: str, expected: PersistenceBackend
) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("DATABASE_URL", URL)
    assert load_settings(env_file=None).persistence_backend is expected


def test_explicit_backend_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("PERSISTENCE_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", URL)
    settings = load_settings(env_file=None)
    assert settings.persistence_backend is PersistenceBackend.POSTGRES
    assert settings.DATABASE_URL is not None
    assert settings.DATABASE_URL.get_secret_value() == URL


def test_database_url_never_appears_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("DATABASE_URL", URL)
    assert "tres-secret" not in repr(load_settings(env_file=None))


@pytest.mark.parametrize("environment", ["dev", "prod"])
def test_postgres_without_url_stops_startup(
    monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)
    with pytest.raises(ConfigurationError, match="DATABASE_URL est obligatoire"):
        load_settings(env_file=None)


def test_memory_is_refused_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("PERSISTENCE_BACKEND", "memory")
    with pytest.raises(ConfigurationError, match="memory interdit en prod"):
        load_settings(env_file=None)


def test_memory_is_allowed_in_dev_without_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("PERSISTENCE_BACKEND", "memory")
    assert load_settings(env_file=None).DATABASE_URL is None


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("PERSISTENCE_BACKEND", "oracle"),
        ("DATABASE_URL", "pas une url"),
        ("DATABASE_URL", ""),
        ("DATABASE_URL", "postgresql+psycopg://u:p@127.0.0.1:5432"),
    ],
)
def test_invalid_persistence_value_names_the_variable(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigurationError, match=name):
        load_settings(env_file=None)


def test_migrations_need_only_the_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)  # ni ENVIRONMENT, ni JWT_SECRET
    assert load_database_url(env_file=None) == URL


@pytest.mark.parametrize("value", [None, "pas une url"])
def test_migrations_without_valid_url_stop(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is not None:
        monkeypatch.setenv("DATABASE_URL", value)
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        load_database_url(env_file=None)
