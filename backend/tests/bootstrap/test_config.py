"""Configuration fail-fast : valeurs valides acceptées, invalides ou manquantes refusées."""

from pathlib import Path

import pytest

from app.bootstrap.config import ConfigurationError, Environment, load_settings


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ENVIRONMENT", "API_PREFIX", "LOG_LEVEL", "PERSISTENCE_BACKEND", "DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)


DEV_URL = "postgresql+psycopg://boutique:secret@127.0.0.1:5432/boutique"


def test_defaults_apply_when_only_environment_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("DATABASE_URL", DEV_URL)
    settings = load_settings(env_file=None)
    assert settings.ENVIRONMENT is Environment.DEV
    assert settings.API_PREFIX == "/api/v1"
    assert settings.LOG_LEVEL == "INFO"


def test_all_variables_are_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("API_PREFIX", "/api/v2")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("DATABASE_URL", DEV_URL)
    settings = load_settings(env_file=None)
    assert (settings.ENVIRONMENT, settings.API_PREFIX, settings.LOG_LEVEL) == (
        Environment.PROD,
        "/api/v2",
        "WARNING",
    )


def test_env_file_is_read(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("ENVIRONMENT=test\nLOG_LEVEL=DEBUG\n", encoding="utf-8")
    settings = load_settings(env_file=env_file)
    assert settings.ENVIRONMENT is Environment.TEST
    assert settings.LOG_LEVEL == "DEBUG"


def test_missing_environment_stops_startup() -> None:
    with pytest.raises(ConfigurationError, match=r"Configuration invalide — ENVIRONMENT"):
        load_settings(env_file=None)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("ENVIRONMENT", "staging"),
        ("API_PREFIX", "api/v1"),
        ("API_PREFIX", "/api/v1/"),
        ("API_PREFIX", ""),
        ("LOG_LEVEL", "verbose"),
    ],
)
def test_invalid_value_stops_startup_naming_the_variable(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("DATABASE_URL", DEV_URL)
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigurationError, match=name):
        load_settings(env_file=None)
