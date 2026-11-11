"""Fixtures partagées : réglages de test, client HTTP, choix de l'adaptateur de persistance.

`--backend=memory|postgres` est reconnu sur **toute** la suite (déclaré ici) :

    uv run pytest                                                       # mémoire (défaut)
    uv run pytest tests/contracts tests/infrastructure/postgres --backend=postgres

Avec `postgres`, une base de test injoignable ou mal configurée fait **échouer** la session
(`pytest.UsageError`), elle ne la saute jamais.
"""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.bootstrap.config import Environment, Settings
from app.bootstrap.container import http_config_from
from app.bootstrap.identity import build_identity
from app.interface.http.app import create_app
from tests.contracts.backends import BACKENDS, DEFAULT_BACKEND, release, require_available

TEST_JWT_SECRET = "secret-de-test-assez-long-pour-hs256-0123456789"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--backend",
        choices=BACKENDS,
        default=DEFAULT_BACKEND,
        help="Adaptateur de persistance sous contrat (tests/contracts, tests/infrastructure).",
    )


def pytest_configure(config: pytest.Config) -> None:
    require_available(str(config.getoption("--backend")))


def pytest_unconfigure(config: pytest.Config) -> None:
    release()


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """`JWT_SECRET` est obligatoire (T08) : fourni à tous les tests par l'environnement."""
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)


@pytest.fixture
def settings() -> Settings:
    return Settings(ENVIRONMENT=Environment.TEST, _env_file=None)


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(http_config_from(settings), build_identity(settings).auth)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    # raise_server_exceptions=False : on observe la réponse 500 réellement envoyée au client.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
