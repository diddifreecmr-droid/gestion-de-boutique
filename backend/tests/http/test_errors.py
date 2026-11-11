"""Traduction des erreurs en enveloppe `{"error": {...}}` (specs § 6.1 à 6.2)."""

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.domain.shared.errors import Conflict, DomainError, Forbidden, NotFound, ValidationFailed


class StockInsufficient(DomainError):
    """Règle métier sans statut dédié : doit donner 422."""

    code = "STOCK_INSUFFICIENT"


class ShopNotFound(NotFound):
    """Sous-classe : hérite du statut de son parent."""

    code = "SHOP_NOT_FOUND"


class Payload(BaseModel):
    name: str
    quantity: int


SECRET = "trace-secrete-ne-doit-pas-fuiter"


@pytest.fixture
def app(app: FastAPI) -> FastAPI:
    errors: dict[str, DomainError] = {
        "validation": ValidationFailed("Champ invalide", details={"field": "x"}),
        "not-found": NotFound("Introuvable"),
        "forbidden": Forbidden("Accès refusé"),
        "conflict": Conflict("Déjà modifié", details={"version": 3}),
        "rule": StockInsufficient("Stock insuffisant", details={"available": 2}),
        "shop": ShopNotFound("Boutique introuvable"),
    }

    @app.get("/test/domain/{kind}")
    async def raise_domain(kind: str) -> None:
        raise errors[kind]

    @app.post("/test/payload")
    async def accept(payload: Payload) -> Payload:
        return payload

    @app.get("/test/boom")
    async def boom() -> None:
        raise RuntimeError(SECRET)

    return app


@pytest.mark.parametrize(
    ("kind", "status", "code", "message", "details"),
    [
        ("validation", 400, "VALIDATION_ERROR", "Champ invalide", {"field": "x"}),
        ("not-found", 404, "NOT_FOUND", "Introuvable", {}),
        ("forbidden", 403, "FORBIDDEN", "Accès refusé", {}),
        ("conflict", 409, "CONFLICT", "Déjà modifié", {"version": 3}),
        ("rule", 422, "STOCK_INSUFFICIENT", "Stock insuffisant", {"available": 2}),
        ("shop", 404, "SHOP_NOT_FOUND", "Boutique introuvable", {}),
    ],
)
def test_domain_error_maps_to_status_and_body(
    client: TestClient, kind: str, status: int, code: str, message: str, details: object
) -> None:
    response = client.get(f"/test/domain/{kind}")
    assert response.status_code == status
    assert response.json() == {"error": {"code": code, "message": message, "details": details}}


def test_request_validation_gives_400_with_fields(client: TestClient) -> None:
    response = client.post("/test/payload", json={"quantity": "pas-un-nombre"})
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    fields = {f["field"]: f["code"] for f in error["details"]["fields"]}
    assert fields == {"body.name": "missing", "body.quantity": "int_parsing"}
    assert "pas-un-nombre" not in response.text  # aucune valeur reçue n'est renvoyée


def test_valid_payload_passes(client: TestClient) -> None:
    response = client.post("/test/payload", json={"name": "Piston", "quantity": 2})
    assert response.status_code == 200


def test_unknown_route_uses_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_wrong_method_uses_error_envelope(client: TestClient) -> None:
    response = client.post("/api/v1/health")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert response.headers["allow"] == "GET"


def test_unexpected_error_gives_500_without_leak_and_is_logged(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR, logger="app.interface.http.errors"):
        response = client.get("/test/boom")
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "INTERNAL_ERROR", "message": "Erreur interne du serveur", "details": {}}
    }
    assert SECRET not in response.text
    assert "Traceback" not in response.text
    records = [r for r in caplog.records if r.name == "app.interface.http.errors"]
    assert len(records) == 1
    assert "GET /test/boom" in records[0].getMessage()
    assert records[0].exc_info is not None
    assert str(records[0].exc_info[1]) == SECRET
