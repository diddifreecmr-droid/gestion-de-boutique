"""Configuration du stockage des pièces jointes (D16) : choix par environnement, variables S3
obligatoires (fail-fast), mémoire interdite en prod, secret jamais affiché, assemblage."""

import pytest

from app.bootstrap.attachments import build_storage
from app.bootstrap.config import ConfigurationError, load_settings
from app.bootstrap.storage_config import StorageBackend
from app.infrastructure.storage.memory import MemoryFileStorage
from app.infrastructure.storage.s3 import S3FileStorage

URL = "postgresql+psycopg://boutique:secret@127.0.0.1:5432/boutique"
S3 = ("S3_ENDPOINT", "S3_ACCESS_KEY", "S3_SECRET_KEY", "S3_BUCKET")


@pytest.fixture(autouse=True)
def _environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ENVIRONMENT", "PERSISTENCE_BACKEND", "STORAGE_BACKEND"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATABASE_URL", URL)


@pytest.mark.parametrize(
    ("environment", "expected"),
    [("test", StorageBackend.MEMORY), ("dev", StorageBackend.S3), ("prod", StorageBackend.S3)],
)
def test_default_backend_depends_on_environment(
    monkeypatch: pytest.MonkeyPatch, environment: str, expected: StorageBackend
) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)
    settings = load_settings(env_file=None)
    assert settings.storage_backend is expected
    assert settings.ATTACHMENT_LINK_TTL_SECONDS == 60
    storage = build_storage(settings)
    assert isinstance(
        storage, MemoryFileStorage if expected is StorageBackend.MEMORY else S3FileStorage
    )


@pytest.mark.parametrize("environment", ["dev", "prod"])
def test_s3_without_its_variables_stops_startup(
    monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)
    for name in S3:
        monkeypatch.delenv(name)
    with pytest.raises(ConfigurationError) as caught:
        load_settings(env_file=None)
    for name in S3:
        assert name in str(caught.value)


def test_memory_is_refused_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("STORAGE_BACKEND", "memory")
    with pytest.raises(ConfigurationError, match="STORAGE_BACKEND=memory interdit en prod"):
        load_settings(env_file=None)


def test_memory_is_allowed_in_dev_and_the_secret_never_shows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("STORAGE_BACKEND", "memory")
    settings = load_settings(env_file=None)
    assert settings.storage_backend is StorageBackend.MEMORY
    assert "test-secret-0123456789" not in repr(settings)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("S3_ENDPOINT", "silo:9000"),
        ("S3_ENDPOINT", "http://silo:9000/chemin"),
        ("S3_BUCKET", "Majuscules"),
        ("S3_REGION", "Europe Ouest"),
        ("STORAGE_BACKEND", "disque"),
        ("ATTACHMENT_LINK_TTL_SECONDS", "2"),
        ("ATTACHMENT_LINK_TTL_SECONDS", "7200"),
    ],
)
def test_invalid_storage_value_names_the_variable(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigurationError, match=name):
        load_settings(env_file=None)
