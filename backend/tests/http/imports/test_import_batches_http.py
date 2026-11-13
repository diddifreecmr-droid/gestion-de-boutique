"""T35 — `GET /imports`, `GET /imports/{id}`, `GET /imports/{id}/errors.xlsx`,
`POST /imports/{id}/cancel` avec les vrais modèles : M3-03, M3-04, SCN-L3-05 (blocage par un
autre lot, annulation, nom libéré), module `import` à venir (403)."""

from io import BytesIO
from typing import Any

import pytest
from openpyxl import load_workbook

from app.application.imports.models import ImportModel
from tests.http.catalog.test_catalog_http import Shop
from tests.http.imports.conftest import Bench

ARTICLES = "Marque;Modèle\nHaojue;HJ125-8\n;HJ200\n".encode()
STOCK = "Marque;Modèle;Lieu;Quantité;Coût unitaire\nHaojue;HJ125-8;Garoua;2;450 000\n".encode()


@pytest.fixture
def bench_models() -> tuple[ImportModel, ...] | None:
    return None  # registre réel (`import_models`)


def _imported(bench: Bench, shop: Shop, who: Any, content: bytes, kind: str) -> Any:
    preview = bench.preview(shop, who, content, kind)
    assert preview.status_code == 200, preview.text
    confirmed = bench.confirm(shop, who, preview.json()["preview_id"])
    assert confirmed.status_code == 201, confirmed.text
    return confirmed.json()


def test_list_detail_and_errors_report(bench: Bench, importable: Shop) -> None:
    owner, accountant = importable.owner, importable.staff["accountant"]
    articles = _imported(bench, importable, accountant, ARTICLES, "articles")
    people = _imported(bench, importable, owner, b"Nom;T\xc3\xa9l\xc3\xa9phone\nAli;690000001\n",
                       "customers")  # fmt: skip
    assert articles["cancellable_until"] == "2026-11-18"
    assert articles["cancelled_at"] is None
    listed = importable.call("GET", "/imports", owner).json()["items"]
    assert [b["number"] for b in listed] == ["IMP-000002", "IMP-000001"]
    mine = importable.call("GET", "/imports", accountant).json()["items"]
    assert [b["number"] for b in mine] == ["IMP-000001"]  # M3-03 : ses modèles seulement
    hidden = importable.call("GET", f"/imports/{people['id']}", accountant)
    assert hidden.status_code == 404
    refused = importable.call("GET", "/imports", importable.staff["seller"])
    assert refused.status_code == 403
    detail = importable.call("GET", f"/imports/{articles['id']}", owner).json()
    assert (detail["imported_by"]["name"], detail["problems_total"]) == ("accountant", 1)
    assert [(i["line"], i["entity"]) for i in detail["items"]] == [(2, "article")]
    report = importable.call("GET", f"/imports/{articles['id']}/errors.xlsx", accountant)
    assert report.status_code == 200
    assert 'filename="erreurs-IMP-000001.xlsx"' in report.headers["content-disposition"]
    sheet = load_workbook(BytesIO(report.content)).active
    assert sheet is not None
    rows = list(sheet.iter_rows(values_only=True))
    assert rows[0] == ("Ligne", "Colonne", "Problème")
    assert rows[1][:2] == (3, "Marque")


def test_cancel_rights_blocking_and_freed_name(bench: Bench, importable: Shop) -> None:
    owner, accountant = importable.owner, importable.staff["accountant"]
    articles = _imported(bench, importable, owner, ARTICLES, "articles")
    stock = _imported(bench, importable, owner, STOCK, "opening_stock")
    path = f"/imports/{articles['id']}/cancel"
    forbidden = importable.call("POST", path, accountant)
    assert forbidden.status_code == 403  # M3-04
    blocked = importable.call("POST", path, owner)
    assert (blocked.status_code, blocked.json()["error"]["code"]) == (422, "IMPORT_CANCEL_BLOCKED")
    assert blocked.json()["error"]["details"]["blocking"] == [
        {"type": "import", "number": "IMP-000002"}
    ]
    undone = importable.call("POST", f"/imports/{stock['id']}/cancel", owner)
    assert (undone.status_code, undone.json()["status"]) == (200, "cancelled")
    assert undone.json()["cancelled_at"] is not None
    assert importable.call("POST", path, owner).status_code == 200
    twice = importable.call("POST", path, owner)
    assert (twice.status_code, twice.json()["error"]["code"]) == (422, "INVALID_STATE_TRANSITION")
    again = _imported(bench, importable, owner, ARTICLES, "articles")  # nom libéré
    assert again["rows_imported"] == 1
    [item] = importable.call("GET", f"/imports/{articles['id']}", owner).json()["items"]
    kept = importable.call("GET", f"/articles/{item['entity_id']}", owner).json()
    assert kept["status"] == "archived"  # rien d'effacé


def test_import_turned_off_by_the_admin_closes_the_batches(bench: Bench, shop: Shop) -> None:
    response = shop.call("GET", "/imports", shop.owner)
    assert (response.status_code, response.json()["error"]["code"]) == (403, "MODULE_DISABLED")
