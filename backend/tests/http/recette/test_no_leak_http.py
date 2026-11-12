"""SEC-N01 à SEC-N04 (critère A4, RG-D02, RG-D03, RG-D05) : balayage de **toutes** les routes.

Pour chaque rôle, chaque route de lecture de `ROUTES` (et les réponses d'écriture et d'erreur
utiles) : (1) aucune clé interdite, à toute profondeur ; (2) aucune valeur sentinelle — coût
543 210, marge 234 567 (= 777 777 − 543 210), prix de vente 777 777, prix de base 780 000.
Un garde-fou compare `ROUTES` à l'OpenAPI : une route nouvelle doit être déclarée ici.
"""

import json
import re
from typing import Any

import pytest

from tests.http.recette.paths import url
from tests.http.recette.routes import ROUTES
from tests.http.recette.routes_trade import cash_sale
from tests.http.recette.world import SENTINEL_COST, SENTINEL_PRICE, Side, World, approval

MARGIN = SENTINEL_PRICE - SENTINEL_COST
SELLER_KEYS = ("cost", "wac", "margin", "value", "fee_share", "stock_value")
# RG-D03 : le comptable ne voit rien des ventes. Seules exceptions, voulues par UC-STK-07
# (INV-06) : le nombre de ventes passées pendant un inventaire en cours et sa phrase.
ACCOUNTANT_KEYS = ("sale", "customer", "receivable", "revenue", "cash_in", "margin",
                   "installment")  # fmt: skip
ACCOUNTANT_ALLOWED = {"sales_since_start", "sales_message"}
DRIVER_KEYS = ("price", "amount", "total", "cost", "wac", "margin", "value")
# Noms de réglages ou de schéma, jamais des montants : marge d'impression du reçu, lieu point
# de vente, champs de saisie du profil, interrupteurs du prix minimum.
SETTING_KEYS = {"margin_mm", "is_point_of_sale", "sale_fields", "min_price_enabled",
                "min_price_requires_approval"}  # fmt: skip
RULES: dict[str, tuple[tuple[str, ...], set[str], tuple[int, ...]]] = {
    "seller": (SELLER_KEYS, set(), (SENTINEL_COST, MARGIN)),
    "accountant": (ACCOUNTANT_KEYS, ACCOUNTANT_ALLOWED, (SENTINEL_PRICE, MARGIN)),
    "driver": (DRIVER_KEYS, set(), (780_000, SENTINEL_COST, SENTINEL_PRICE)),
}


def keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys(v)}
    if isinstance(value, list):
        return {k for item in value for k in keys(item)}
    return set()


def leaks(role: str, body: Any) -> list[str]:
    words, allowed, sentinels = RULES[role]
    found = sorted(k for k in keys(body) - allowed - SETTING_KEYS if any(w in k.lower() for w in words))
    text = json.dumps(body, ensure_ascii=False)
    found += [f"valeur {s}" for s in sentinels if re.search(rf"(?<![\w-]){s}(?![\w-])", text)]
    return found


def _sweep(side: Side, role: str, api_me: Any) -> dict[str, list[str]]:
    who, report = side.sessions[role], {}
    bodies: dict[str, Any] = {"GET /me": api_me}
    for route in ROUTES:
        method, template = route.split(" ", 1)
        if method == "GET":
            response = side.call(method, url(side, template), who)
            bodies[route] = response.json() if response.content else None
    for route, body in bodies.items():
        if found := leaks(role, body):
            report[route] = found
    return report


@pytest.mark.parametrize("role", list(RULES))
def test_no_forbidden_key_nor_sentinel_on_any_read_route(world: World, role: str) -> None:
    side = world.a
    me = world.api.call("GET", "/me", side.sessions[role]).json()
    assert _sweep(side, role, me) == {}


def test_seller_write_and_error_responses_carry_no_cost(world: World) -> None:
    side = world.a
    seller = side.sessions["seller"]
    responses = [
        side.call("POST", "/sales", seller, json=cash_sale(side)),
        side.call("POST", f"/receivables/{side.ids['receivable_seller']}/installments", seller,
                  json={"amount": 1_000, "mode_id": side.ids["cash"]}),
        side.call("POST", f"/sales/{side.ids['sale_seller']}/error-reports", seller,
                  json={"description": "erreur"}),
        side.call("POST", "/sales", seller, json={**cash_sale(side), "lines": [
            {"article_id": side.ids["article"], "quantity": "30", "unit_price": 1}],
            "payments": [{"mode_id": side.ids["cash"], "amount": 30}]}),
    ]  # fmt: skip
    limited = side.ok("POST", "/customers", seller,
                      json={"name": "Plafond", "phone": "655000001", "credit_limit": 100_000})  # fmt: skip
    credit = {**cash_sale(side), "kind": "credit", "payments": [],
              "customer": {"id": limited["id"]}}  # fmt: skip
    responses.append(side.call("POST", "/sales", seller, json=credit))
    approval(side, True)
    responses.append(side.call("POST", "/sales", seller, json=cash_sale(side, 700_000)))
    codes = [r.json().get("error", {}).get("code") for r in responses]
    assert codes == [None, None, None, "STOCK_INSUFFICIENT", "CREDIT_LIMIT_EXCEEDED",
                     "PRICE_BELOW_MINIMUM"]  # fmt: skip
    assert [leaks("seller", r.json()) for r in responses] == [[]] * len(responses)


def test_owner_receipt_never_carries_a_cost(world: World) -> None:
    side = world.a  # SEC-N04 : jamais de coût sur un reçu, même pour le propriétaire
    receipt = side.ok("GET", f"/sales/{side.ids['sale_seller']}/receipt", side.owner)
    assert leaks("seller", receipt) == []
    sale = side.ok("GET", f"/sales/{side.ids['sale_seller']}", side.owner)
    assert {"frozen_last_cost", "frozen_wac", "margin", "margin_wac"} <= keys(sale)


def test_route_table_matches_openapi(world: World) -> None:
    prefix = "/api/v1/shops/{shop_id}"
    paths = world.api.client.app.openapi()["paths"]  # type: ignore[attr-defined]
    declared = {
        f"{method.upper()} {path.removeprefix(prefix)}"
        for path, operations in paths.items()
        if path.startswith(prefix)
        for method in operations
    }
    assert declared == set(ROUTES)


def test_the_scan_finds_nested_keys_and_sentinels() -> None:
    nested = {"items": [{"lines": [{"frozen_wac": 1}]}], "error": {"details": {"x": 543_210}}}
    assert leaks("seller", nested) == ["frozen_wac", "valeur 543210"]
    assert leaks("seller", {"id": "01a1-543210ab"}) == []  # pas dans un identifiant
