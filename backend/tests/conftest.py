"""Fixtures partagées : réglages de test et client HTTP sur l'application assemblée."""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.bootstrap.config import Environment, Settings
from app.bootstrap.container import http_config_from
from app.interface.http.app import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(ENVIRONMENT=Environment.TEST, _env_file=None)


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(http_config_from(settings))


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    # raise_server_exceptions=False : on observe la réponse 500 réellement envoyée au client.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
