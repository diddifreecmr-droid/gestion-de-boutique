"""Routes des ventes : contrat § 6.4 (SCN-01 7a/7b), non-fuite des coûts sur toutes les routes de
ventes, reçu et erreurs compris (SEC-N01, SEC-N04), droits (comptable, chauffeur : 403), 404
entre vendeurs, idempotence (SAL-06), formes d'erreur lues par l'écran de vente."""

from typing import Any

from app.domain.sales.ids import ErrorReportId, SaleId
from tests.http.catalog.test_catalog_http import Shop, _keys
from tests.http.purchasing.test_purchasing_http import bought
from tests.http.shops.conftest import Api, Session

LEAKS = ("cost", "wac", "margin", "value", "fee_share", "unit_cost", "stock_value", "margin_rate")
OWNER_COSTS = {"frozen_last_cost", "frozen_wac", "margin", "margin_wac"}


def leaked(body: object) -> list[str]:
    return sorted(k for k in _keys(body) if any(word in k for word in LEAKS))


def cash_mode(shop: Shop) -> str:
    modes = shop.call("GET", "/payment-modes", shop.owner).json()
    return str(next(m["id"] for m in modes if m["name"] == "Espèces"))


def credit_body(article: dict[str, Any], mode: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": str(SaleId.new()),
        "kind": "credit",
        "customer": {"id": None, "name": "Moussa A.", "phone": "+237690000000",
                     "kind": "individual"},
        "lines": [
            {"article_id": article["id"], "sale_mode": "unit", "quantity": "1",
             "unit_price": 780_000,
             "details": [{"color": "Rouge", "chassis_number": "LBX123", "engine_number": None}]}
        ],
        "payments": [{"mode_id": mode, "amount": 300_000, "reference": None}],
        "credit": {"reminder_on": "2026-12-01", "terms": "100 000 par mois", "guarantor": None},
        "price_request_id": None,
        "note": None,
        **extra,
    }  # fmt: skip


def sold(api: Api) -> tuple[Shop, dict[str, Any], dict[str, Any], Session]:
    shop, article, _ = bought(api)
    seller = shop.staff["seller"]
    created = shop.call("POST", "/sales", seller, json=credit_body(article, cash_mode(shop)))
    assert created.status_code == 201, created.text
    return shop, article, created.json(), seller


def test_section_64_contract_and_no_cost_leak(api: Api) -> None:
    shop, _, sale, seller = sold(api)
    assert (sale["number"], sale["status"], sale["kind"]) == ("V-000001", "valid", "credit")
    assert (sale["total"], sale["paid"], sale["remaining"]) == (780_000, 300_000, 480_000)
    assert sale["receivable"] == {"id": sale["id"], "remaining": 480_000}  # créance T17
    assert sale["warnings"] == []
    [line] = sale["lines"]
    assert (line["article_name"], line["quantity"], line["line_total"]) == (
        "Haojue HJ125-8",
        "1",
        780_000,
    )
    path = f"/sales/{sale['id']}"
    owner_view = shop.call("GET", path, shop.owner).json()["lines"][0]
    assert {k: owner_view[k] for k in OWNER_COSTS} == {
        "frozen_last_cost": 540_000, "frozen_wac": 540_000, "margin": 240_000,
        "margin_wac": 240_000,
    }  # fmt: skip
    report = shop.call(
        "POST", f"{path}/error-reports", seller, json={"description": "mauvais prix"}
    )
    assert report.status_code == 201, report.text
    customer_id = sale["customer_id"]
    bodies = [
        sale,
        shop.call("GET", path, seller).json(),
        shop.call("GET", "/sales", seller).json(),
        shop.call("GET", "/sales?q=lbx123&from=2026-01-01", seller).json(),
        shop.call("GET", f"{path}/receipt", seller).json(),
        report.json(),
        shop.call("GET", "/customers", seller).json(),
        shop.call("GET", f"/customers/{customer_id}", seller).json(),
    ]
    for body in bodies:  # SEC-N01 : aucune clé de coût, même vide
        assert leaked(body) == [], body
    receipt = shop.call("GET", f"{path}/receipt", shop.owner).json()
    assert leaked(receipt) == []  # SEC-N04 : même pour le propriétaire
    assert [m["code"] for m in receipt["mentions"]] == ["credit_sale", "duplicate"]
    assert receipt["header"]["shop_name"] == "Motos Garoua"
    assert receipt["payments"] == [{"mode_name": "Espèces", "amount": 300_000, "reference": None}]


def test_rights_idempotence_and_cross_seller_404(api: Api) -> None:
    shop, article, sale, seller = sold(api)
    path = f"/sales/{sale['id']}"
    for role in ("accountant", "driver"):  # RG-D03
        who = shop.staff[role]
        for method, suffix in (("GET", "/sales"), ("GET", path), ("GET", "/customers")):
            assert shop.call(method, suffix, who).status_code == 403
    replay = credit_body(article, cash_mode(shop), id=sale["id"])
    again = shop.call("POST", "/sales", seller, json=replay)
    assert (again.status_code, again.json()["number"]) == (200, "V-000001")
    cancel = shop.call("POST", f"{path}/cancel", seller, json={"reason": "x"})
    assert cancel.status_code == 403
    assert shop.call("POST", f"{path}/cancel", shop.owner, json={}).status_code == 400
    done = shop.call("POST", f"{path}/cancel", shop.owner, json={"reason": "client a renoncé"})
    assert (done.status_code, done.json()["status"]) == (200, "cancelled")
    patch = {"version": 2, "reason": "x", "lines": [{"unit_price": 1}]}
    refused = shop.call("PATCH", path, shop.owner, json=patch)
    assert refused.json()["error"]["code"] == "INVALID_STATE_TRANSITION"
    missing = f"/error-reports/{ErrorReportId.new()}/reply"
    assert shop.call("POST", missing, shop.owner, json={"reply": "ok"}).status_code == 404


def test_error_shapes_for_the_sale_screen(api: Api) -> None:
    shop, article, _, seller = sold(api)
    mode = cash_mode(shop)
    duplicate = shop.call("POST", "/sales", seller, json=credit_body(article, mode))
    error = duplicate.json()["error"]
    assert (duplicate.status_code, error["code"]) == (409, "DUPLICATE")
    assert {k: error["details"][k] for k in ("field", "value", "sale_number")} == {
        "field": "chassis_number",
        "value": "LBX123",
        "sale_number": "V-000001",
    }
    body = credit_body(article, mode)
    body["lines"][0].update(quantity="30", details=[])
    short = shop.call("POST", "/sales", seller, json=body).json()["error"]
    assert short["code"] == "STOCK_INSUFFICIENT"
    assert (short["details"]["article_id"], short["details"]["available"]) == (article["id"], "19")
    assert short["details"]["other_locations"] == []
    assert leaked(short) == []
    body = credit_body(article, mode, customer=None)
    body["lines"][0]["details"] = []
    assert shop.call("POST", "/sales", seller, json=body).status_code == 400  # SAL-07
    best = shop.call("GET", "/articles?sort=best_selling", shop.owner)
    assert [a["id"] for a in best.json()["items"]] == [article["id"]]


def test_owner_patch_and_customer_routes(api: Api) -> None:
    shop, article, sale, seller = sold(api)
    mode = cash_mode(shop)
    patch = {
        "version": 1,
        "reason": "mauvais prix",
        "lines": [{"article_id": article["id"], "quantity": "1", "unit_price": 760_000,
                   "details": [{"chassis_number": "LBX124"}]}],
        "payments": [{"mode_id": mode, "amount": 300_000}],
        "note": "corrigée",
    }  # fmt: skip
    changed = shop.call("PATCH", f"/sales/{sale['id']}", shop.owner, json=patch).json()
    assert (changed["remaining"], changed["lines"][0]["margin"]) == (460_000, 220_000)
    wrong = {"version": 2, "reason": "x", "lines": [{"quantity": "2"}]}
    refused = shop.call("PATCH", f"/sales/{sale['id']}", shop.owner, json=wrong).json()
    assert refused["error"]["code"] == "LINE_CHANGE_NOT_ALLOWED"
    bad = {"version": 2, "reason": "x", "lines": [{"quantity": "abc"}]}
    assert shop.call("PATCH", f"/sales/{sale['id']}", shop.owner, json=bad).status_code == 400
    body = {"name": "Awa", "phone": "677 11 22 33", "credit_limit": 500_000}
    created = shop.call("POST", "/customers", seller, json=body)
    assert created.status_code == 201, created.text
    customer = created.json()
    assert customer["phone"] == "+237677112233"
    path = f"/customers/{customer['id']}"
    updated = shop.call("PATCH", path, seller, json={"version": 1, "city": "Garoua"}).json()
    assert updated["city"] == "Garoua"
    cleared = shop.call("PATCH", path, seller, json={"version": 2, "name": None})
    assert cleared.status_code == 400
    twin = shop.call("POST", "/customers", shop.owner, json=body).json()["error"]
    assert (twin["code"], twin["details"]["existing_id"]) == ("DUPLICATE", customer["id"])
    found = shop.call("GET", "/customers?q=awa", seller).json()["items"]
    assert [c["id"] for c in found] == [customer["id"]]
