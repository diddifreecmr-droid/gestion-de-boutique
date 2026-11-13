"""Routes de l'import (UC-IMP-01, UC-IMP-02) : module `import` à venir (403 tant que T46 n'est
pas livrée), modèle `.xlsx` téléchargé (IMP-01, IMP-02), aperçu (IMP-04, IMP-05), droits."""

import io
from typing import Any

from openpyxl import load_workbook

from app.domain.imports.errors import ImportPreviewExpired
from app.interface.http.errors import status_for
from tests.http.catalog.test_catalog_http import Shop
from tests.http.imports.conftest import Bench

PREFIX = "/api/v1/shops/{shop_id}"
ROUTES = ("GET /imports/templates/{kind}", "POST /imports/preview")
CSV = b"Nom;Prix\nChemise;9 000\nPantalon;\nRobe;1 250 000 FCFA\n"


def _openapi(bench: Bench) -> dict[str, Any]:
    paths: dict[str, Any] = bench.api.client.app.openapi()["paths"]  # type: ignore[attr-defined]
    return paths


def test_routes_declare_the_import_module(bench: Bench) -> None:
    paths = _openapi(bench)
    for route in ROUTES:
        method, path = route.split(" ", 1)
        assert paths[f"{PREFIX}{path}"][method.lower()]["x-module"] == "import"


def test_import_stays_an_upcoming_module_closed_for_every_shop(bench: Bench, shop: Shop) -> None:
    for who in (shop.owner, shop.staff["accountant"]):
        responses = [
            shop.call("GET", "/imports/templates/articles", who),
            bench.preview(shop, who, CSV),
        ]
        for response in responses:
            assert response.status_code == 403, response.text
            assert response.json()["error"]["code"] == "MODULE_DISABLED"
            assert response.json()["error"]["details"] == {"module": "import"}
    opened = bench.api.open_motos(bench.api.admin(), owner_phone="690000009")
    stranger = bench.api.login("690000009", opened["temporary_pin"])
    for response in (  # non-membre : 404 d'abord, avant le module
        shop.call("GET", "/imports/templates/articles", stranger),
        bench.preview(shop, stranger, CSV),
    ):
        assert response.status_code == 404, response.text
    body = {"modules": ["audit", "catalog", "core", "import", "sales"]}
    refused = bench.api.call("PATCH", f"/platform/shops/{shop.id}", bench.api.admin(), json=body)
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "MODULE_NOT_YET_AVAILABLE"
    assert bench.storage.keys() == []


def test_template_download(bench: Bench, importable: Shop) -> None:
    response = importable.call("GET", "/imports/templates/articles", importable.owner)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response.headers["content-disposition"] == (
        'attachment; filename="modele-import-articles.xlsx"'
    )
    assert response.headers["cache-control"] == "private, no-store"
    workbook = load_workbook(io.BytesIO(response.content))
    assert workbook.sheetnames == ["Articles", "Mode d'emploi", "Listes"]
    header = [c.value for c in workbook["Articles"][1]]
    assert header == ["Nom *", "Prix *", "Lieu", "Catégorie"]
    validations = workbook["Articles"].data_validations.dataValidation
    assert [str(v.sqref) for v in validations] == ["C2:C5001"]  # lieux ; aucune catégorie
    for kind in ("trucks", "drivers", "customers"):  # IMP-02 (+ modèle non encore branché)
        missing = importable.call("GET", f"/imports/templates/{kind}", importable.owner)
        assert missing.status_code == 404, kind
    seller = importable.call("GET", "/imports/templates/articles", importable.staff["seller"])
    assert (seller.status_code, seller.json()["error"]["code"]) == (403, "FORBIDDEN")
    accountant = importable.staff["accountant"]
    assert importable.call("GET", "/imports/templates/articles", accountant).status_code == 200
    blocked = importable.call("GET", "/imports/templates/receivables", accountant)
    assert blocked.status_code == 403


def test_preview(bench: Bench, importable: Shop) -> None:
    response = bench.preview(importable, importable.owner, CSV)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert set(body) == {
        "preview_id", "kind", "expires_at", "rows_read", "rows_valid", "rows_ignored",
        "problems", "problems_total", "notes",
    }  # fmt: skip
    assert (body["kind"], body["rows_read"], body["rows_valid"], body["rows_ignored"]) == (
        "articles", 3, 2, 1,
    )  # fmt: skip
    assert body["problems"] == [
        {"line": 3, "column": "Prix", "message": "le prix est vide",
         "text": "Ligne 3 : le prix est vide"},
    ]  # fmt: skip
    assert body["notes"] == ["2 articles nouveaux seront créés"]
    [key] = bench.storage.keys()
    assert key == f"shops/{importable.id}/imports/{body['preview_id']}.bin"
    assert key not in response.text  # aucune clé de stockage renvoyée (SEC-N3-03)


def test_preview_refusals(bench: Bench, importable: Shop) -> None:
    owner = importable.owner
    xls = bench.preview(importable, owner, b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 32)
    assert (xls.status_code, xls.json()["error"]["code"]) == (400, "IMPORT_FILE_INVALID")
    assert "xls" in xls.json()["error"]["details"]["reason"]
    empty = bench.preview(importable, owner, b"Nom;Prix\n")
    assert (empty.status_code, empty.json()["error"]["code"]) == (400, "IMPORT_FILE_INVALID")
    too_many = bench.preview(importable, owner, ("Nom;Prix\n" + "a;1\n" * 5_001).encode())
    assert too_many.status_code == 422
    assert too_many.json()["error"] == {
        "code": "IMPORT_TOO_MANY_ROWS",
        "message": "Trop de lignes : 5001 lues, 5000 au plus par fichier",
        "details": {"max": 5_000, "rows": 5_001},
    }
    unknown = bench.preview(importable, owner, CSV, kind="trucks")
    assert unknown.status_code == 404
    seller = bench.preview(importable, importable.staff["seller"], CSV)
    assert seller.status_code == 403
    no_kind = importable.call("POST", "/imports/preview", owner, files={"file": ("a.csv", CSV)})
    assert no_kind.status_code == 400
    bench.storage.available = False
    down = bench.preview(importable, owner, CSV)
    assert (down.status_code, down.json()["error"]["code"]) == (503, "STORAGE_UNAVAILABLE")
    bench.storage.available = True
    assert bench.storage.keys() == []


def test_an_expired_preview_is_gone() -> None:
    assert status_for(ImportPreviewExpired("x")) == 410
