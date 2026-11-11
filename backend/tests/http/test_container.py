"""Composition root : assemble l'application depuis l'environnement, échoue sinon."""

import logging

import pytest
from fastapi.testclient import TestClient

from app.bootstrap.config import ConfigurationError
from app.bootstrap.container import build_app


def test_build_app_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    with TestClient(build_app(env_file=None)) as client:
        assert client.get("/api/v1/health").json() == {"status": "ok"}
    assert logging.getLogger("app").level == logging.DEBUG


def test_build_app_refuses_to_start_without_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    with pytest.raises(ConfigurationError, match="ENVIRONMENT"):
        build_app(env_file=None)
