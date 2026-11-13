"""Effets d'un module éteint sur les autres (specs § 15.1) et boutique minimale de bout en bout.

- sans `receivables` : ni vente ni échange à crédit (403 `MODULE_DISABLED`, rien d'écrit) ;
  bloc créances du tableau de bord et rappels du vendeur à `null` ;
- sans `expenses` : aucune dépense dans les chiffres (`summary.expenses = null`, résultat =
  marge), dépenses du comptable à `null`, détail « dépenses » refusé ;
- sans `transfers`/`transport` : déplacements, camions et blocs du chauffeur à `null`.
"""

from typing import Any

from app.domain.profiles.modules import ALL_MODULES, MANDATORY_MODULES, Module
from app.domain.sales.ids import SaleId
from tests.http.recette.routes_trade import cash_sale
from tests.http.recette.test_modules_routes_http import set_modules
from tests.http.recette.world import HJ, SENTINEL_PRICE, World, open_shop


def _refused(response: Any, module: str) -> None:
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "MODULE_DISABLED"
    assert response.json()["error"]["details"] == {"module": module}


def test_without_receivables_no_credit_no_credit_exchange(world: World) -> None:
    a = world.a
    set_modules(world, a, ALL_MODULES - {Module.RECEIVABLES})
    seller = a.sessions["seller"]
    a.ok("POST", "/sales", seller, json=cash_sale(a))  # le comptant marche
    credit = {
        "id": str(SaleId.new()), "kind": "credit",
        "customer": {"name": "Awa", "phone": "+237690000055", "kind": "individual"},
        "lines": [{"article_id": a.ids["article"], "quantity": "1", "unit_price": SENTINEL_PRICE}],
        "payments": [], "credit": {"reminder_on": "2026-12-01"},
    }  # fmt: skip
    _refused(a.call("POST", "/sales", seller, json=credit), "receivables")
    assert a.call("GET", f"/sales/{credit['id']}", a.owner).status_code == 404
    sale = a.ids["sale_seller"]
    exchange = {
        "lines": [{"line": 1, "quantity": "1", "chassis": ["LBX123"]}], "reason": "échange",
        "exchange": {"mode_id": a.ids["cash"],
                     "sale": {**credit, "id": str(SaleId.new()), "customer": None}},
    }  # fmt: skip
    _refused(a.call("POST", f"/sales/{sale}/returns", a.owner, json=exchange), "receivables")
    assert a.ok("GET", f"/sales/{sale}/returns", a.owner)["returns"] == []  # retour annulé aussi
    dashboard = a.ok("GET", "/dashboard", a.owner)
    assert dashboard["receivables"] is None
    assert a.ok("GET", "/home", seller)["seller"]["reminders_due"] is None
    assert world.b.ok("GET", "/dashboard", world.b.owner)["receivables"]["total_due"] > 0


def test_without_expenses_no_expense_enters_the_figures(world: World) -> None:
    a = world.a
    with_expenses = a.ok("GET", "/dashboard", a.owner)["summary"]
    assert with_expenses["expenses"]["value"] > 0  # dépenses du jeu (25 000 + 1 000)
    set_modules(world, a, ALL_MODULES - {Module.EXPENSES})
    summary = a.ok("GET", "/dashboard", a.owner)["summary"]
    assert summary["expenses"] is None
    assert summary["result"] == summary["margin"]
    assert a.ok("GET", "/home", a.sessions["accountant"])["accountant"]["expenses"] is None
    _refused(a.call("GET", "/dashboard/details/expenses", a.owner), "expenses")
    set_modules(world, a, ALL_MODULES)
    assert a.ok("GET", "/dashboard", a.owner)["summary"] == with_expenses


def test_without_transfers_and_transport_their_blocks_are_null(world: World) -> None:
    a = world.a
    full = a.ok("GET", "/dashboard", a.owner)
    assert full["stock"]["in_transit"]["available"] is False  # Lot 2 : non disponible
    assert full["trucks"] is not None
    set_modules(world, a, ALL_MODULES - {Module.TRANSFERS, Module.TRANSPORT})
    dashboard = a.ok("GET", "/dashboard", a.owner)
    assert (dashboard["stock"]["in_transit"], dashboard["trucks"]) == (None, None)
    accountant = a.ok("GET", "/home", a.sessions["accountant"])["accountant"]
    assert accountant["transfers_to_receive"] is None
    driver = a.ok("GET", "/home", a.sessions["driver"])["driver"]
    assert driver == {"current_trip": None, "trip_expenses": None}


def test_minimal_shop_sells_cash_end_to_end(world: World) -> None:
    shop = open_shop(world.api, world.admin, "Motos Maroua", "690000201", "6772000")
    opened = set_modules(world, shop, MANDATORY_MODULES)
    assert set(opened["enabled_modules"]) == {"core", "audit", "catalog", "sales"}
    owner, seller = shop.owner, shop.sessions["seller"]
    profile = shop.ok("GET", "/profile", owner)
    assert set(profile["enabled_modules"]) == MANDATORY_MODULES
    article = shop.ok("POST", "/articles", owner, json={**HJ, "base_price": 780_000})
    shop.ids["article"] = article["id"]
    modes = shop.ok("GET", "/payment-modes", owner)
    shop.ids["cash"] = next(m["id"] for m in modes if m["name"] == "Espèces")
    shop.ok("POST", "/adjustments", owner, json={
        "location_id": shop.ids["garoua"], "article_id": article["id"], "direction": "in",
        "quantity": "2", "reason": "entry_error",
    })  # fmt: skip
    _refused(shop.call("POST", "/purchases", owner, json={}), "purchases")
    sale = shop.ok("POST", "/sales", seller, json=cash_sale(shop, 780_000))
    assert (sale["number"], sale["kind"], sale["total"]) == ("V-000001", "cash", 780_000)
    assert shop.ok("GET", f"/sales/{sale['id']}/receipt", seller)
    assert [s["id"] for s in shop.ok("GET", "/sales", owner)["items"]] == [sale["id"]]
    assert shop.ok("GET", "/home", seller)["seller"]["sales_amount"] == 780_000
    _refused(shop.call("GET", "/dashboard", owner), "dashboard")
    entries = shop.ok("GET", "/audit", owner)["items"]
    assert any(e["entity"]["type"] == "sale" for e in entries)
