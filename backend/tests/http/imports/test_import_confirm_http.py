"""`POST /imports` avec les **vrais** modèles (T33, T34) : 201 puis 200 (IMP-09), module `import`
à venir (403), droits par modèle (M3-01, M3-02), modules exigés (IMP-11), aperçu d'une autre
boutique (SEC-I3-01), coûts jamais montrés au vendeur (RG-D02)."""

from typing import Any

import pytest

from app.application.imports.models import ImportModel
from app.domain.profiles.modules import AVAILABLE_MODULES, Module
from tests.http.catalog.test_catalog_http import Shop
from tests.http.imports.conftest import Bench

ARTICLES = b"Marque;Mod\xc3\xa8le\nHaojue;HJ125-8\nHaojue;HJ125-8\n"
STOCK = "Marque;Modèle;Lieu;Quantité;Coût unitaire\nHaojue;HJ125-8;Garoua;2;450 000\n".encode()


@pytest.fixture
def bench_models() -> tuple[ImportModel, ...] | None:
    return None  # registre réel (`import_models`)


def _imported(bench: Bench, shop: Shop, who: Any, content: bytes, kind: str) -> Any:
    preview = bench.preview(shop, who, content, kind)
    assert preview.status_code == 200, preview.text
    return bench.confirm(shop, who, preview.json()["preview_id"])


def test_confirm_writes_once_and_replays(bench: Bench, importable: Shop) -> None:
    owner = importable.owner
    preview = bench.preview(importable, owner, ARTICLES)
    assert preview.json()["notes"] == ["1 article nouveau sera créé"]
    preview_id = preview.json()["preview_id"]
    first = bench.confirm(importable, owner, preview_id)
    assert first.status_code == 201, first.text
    body = first.json()
    assert (body["number"], body["kind"], body["status"]) == ("IMP-000001", "articles", "imported")
    assert (body["rows_read"], body["rows_imported"], body["rows_ignored"]) == (2, 1, 1)
    assert body["created"] == [{"entity": "article", "count": 1}]
    again = bench.confirm(importable, owner, preview_id)
    assert (again.status_code, again.json()["id"]) == (200, body["id"])
    unknown = bench.confirm(importable, owner, "0190f0c2-0000-7000-8000-000000000000")
    assert unknown.status_code == 404
    garbled = bench.confirm(importable, owner, "pas-un-identifiant")
    assert garbled.status_code in {400, 422}


def test_import_turned_off_by_the_admin_closes_confirmation(bench: Bench, shop: Shop) -> None:
    response = bench.confirm(shop, shop.owner, "0190f0c2-0000-7000-8000-000000000000")
    assert (response.status_code, response.json()["error"]["code"]) == (403, "MODULE_DISABLED")


def test_rights_modules_and_costs(bench: Bench, importable: Shop) -> None:
    accountant, seller = importable.staff["accountant"], importable.staff["seller"]
    assert _imported(bench, importable, accountant, ARTICLES, "articles").status_code == 201
    stock = _imported(bench, importable, accountant, STOCK, "opening_stock")
    assert stock.status_code == 201, stock.text
    assert stock.json()["created"] == [{"entity": "stock_movement", "count": 1}]
    for kind in ("customers", "receivables"):  # M3-02 : refusés au comptable
        refused = bench.preview(importable, accountant, b"Nom\nAli\n", kind)
        assert (refused.status_code, refused.json()["error"]["code"]) == (403, "FORBIDDEN")
    forbidden = bench.preview(importable, seller, ARTICLES)
    assert forbidden.status_code == 403
    [article] = importable.call("GET", "/articles", seller).json()["items"]
    assert "wac" not in article
    assert "last_cost" not in article
    owner_view = importable.call("GET", f"/articles/{article['id']}", importable.owner).json()
    assert (owner_view["wac"], owner_view["last_cost"]) == (450_000, 450_000)
    body = {"modules": ["audit", "catalog", "core", "import", "sales"]}
    admin = bench.api.admin()
    patched = bench.api.call("PATCH", f"/platform/shops/{importable.id}", admin, json=body)
    assert patched.status_code == 200, patched.text
    for kind in ("receivables", "suppliers"):  # IMP-11
        closed = bench.preview(importable, importable.owner, b"Nom\nAli\n", kind)
        assert (closed.status_code, closed.json()["error"]["code"]) == (403, "MODULE_DISABLED")


def test_a_preview_of_another_shop_is_unknown(bench: Bench, importable: Shop) -> None:
    preview = bench.preview(importable, importable.owner, ARTICLES)
    opened = bench.api.open_motos(bench.api.admin(), owner_phone="690000009")
    stranger = bench.api.login("690000009", opened["temporary_pin"])
    other_id = opened["shop"]["shop_id"]
    modules = {"modules": sorted({*AVAILABLE_MODULES, Module.IMPORT})}
    admin = bench.api.admin()
    enabled = bench.api.call("PATCH", f"/platform/shops/{other_id}", admin, json=modules)
    assert enabled.status_code == 200, enabled.text
    body = {"preview_id": preview.json()["preview_id"]}
    response = bench.api.call("POST", f"/shops/{other_id}/imports", stranger, json=body)
    assert response.status_code == 404  # SEC-I3-01 : l'aperçu de A n'existe pas pour B
    assert importable.call("GET", "/articles", importable.owner).json()["items"] == []
