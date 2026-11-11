"""Sonde de vie et exposition de la documentation selon l'environnement."""

from fastapi.testclient import TestClient

from app.bootstrap.config import Environment, Settings
from app.bootstrap.container import http_config_from
from app.interface.http.app import create_app


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_follows_configured_prefix() -> None:
    settings = Settings(ENVIRONMENT=Environment.TEST, API_PREFIX="/v9", _env_file=None)
    with TestClient(create_app(http_config_from(settings))) as client:
        assert client.get("/v9/health").json() == {"status": "ok"}
        assert client.get("/api/v1/health").status_code == 404


def test_openapi_is_exposed_outside_production(client: TestClient) -> None:
    assert client.get("/api/v1/openapi.json").status_code == 200


def test_openapi_is_hidden_in_production() -> None:
    settings = Settings(ENVIRONMENT=Environment.PROD, _env_file=None)
    with TestClient(create_app(http_config_from(settings))) as client:
        assert client.get("/api/v1/openapi.json").status_code == 404
        assert client.get("/api/v1/docs").status_code == 404
