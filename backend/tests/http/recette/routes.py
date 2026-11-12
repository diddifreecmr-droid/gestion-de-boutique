"""Table des routes de boutique du Lot 1 : pour chacune, un corps **valide** (une requête
refusée par la validation ne prouverait rien sur les droits ni sur l'isolation).

`ROUTES` couvre **toutes** les routes `/shops/{shop_id}…` de l'OpenAPI : le garde-fou
`test_route_table_matches_openapi` échoue si une route nouvelle n'y est pas déclarée.
"""

from collections.abc import Mapping
from typing import Any

from tests.http.recette.paths import Body, listed, phone, unique, versioned
from tests.http.recette.routes_trade import TRADE_ROUTES
from tests.http.recette.world import HJ, Side


def _article(side: Side) -> dict[str, Any]:
    return {"fields": {**HJ["fields"], "model": unique("HJ")}}


SHOP_ROUTES: Mapping[str, Body | None] = {
    "GET /audit": None,
    "GET /audit/entities/{entity_type}/{entity_id}": None,
    "GET /audit/users/{user_id}": None,
    "GET /alerts": None,
    "POST /alerts/{alert_id}/read": None,
    "GET /profile": None,
    "GET /settings": None,
    "PATCH /settings": versioned("/settings", copies=2),
    "GET /locations": None,
    "POST /locations": lambda s: {"name": unique("Dépôt"), "kind": "warehouse",
                                  "is_point_of_sale": False},
    "PATCH /locations/{location_id}": listed("/locations", "garoua", city="Maroua"),
    "GET /payment-modes": None,
    "POST /payment-modes": lambda s: {"name": unique("Wave")},
    "PATCH /payment-modes/{mode_id}": listed("/payment-modes", "cash", display_order=9),
    "GET /members": None,
    "POST /members": lambda s: {"name": unique("Awa"), "phone": phone(), "role": "accountant"},
    "PATCH /members/{user_id}": lambda s: {"version": _member_version(s), "role": "accountant"},
    "POST /members/{user_id}/reset-pin": None,
    "POST /members/{user_id}/revoke-devices": None,
    "POST /members/{user_id}/unlock": None,
    "GET /admin-access": None,
    "POST /admin-access": None,
    "DELETE /admin-access": None,
    "GET /articles": None,
    "POST /articles": _article,
    "GET /articles/{article_id}": None,
    "PATCH /articles/{article_id}": versioned("/articles/{article_id}", notes="vu"),
    "PUT /articles/{article_id}/prices": versioned("/articles/{article_id}", base_price=780_000),
    "POST /articles/{article_id}/archive": None,
    "POST /articles/{article_id}/reactivate": None,
    "GET /expenses": None,
    "POST /expenses": lambda s: {"amount": 5_000, "category_id": s.ids["fuel"]},
    "GET /expenses/{expense_id}": None,
    "PATCH /expenses/{expense_id}": versioned("/expenses/{expense_id}", beneficiary="Total"),
    "POST /expenses/{expense_id}/cancel": lambda s: {"reason": "doublon"},
    "GET /expenses/{expense_id}/repeat": None,
    "GET /expense-categories": None,
    "POST /expense-categories": lambda s: {"name": unique("Gardiennage")},
    "PATCH /expense-categories/{category_id}": listed(
        "/expense-categories", "fuel", display_order=9),
    "GET /tags": None,
    "POST /tags/merge": lambda s: {"source_id": s.ids["tag"], "target_id": s.ids["tag2"]},
    "GET /stock": None,
    "GET /stock/value": None,
    "GET /stock/damaged": None,
    "GET /articles/{article_id}/movements": None,
    "POST /adjustments": lambda s: {"location_id": s.ids["garoua"], "article_id": s.ids["article"],
                                    "direction": "in", "quantity": "1", "reason": "entry_error"},
    "POST /inventories": lambda s: {"location_id": s.ids["garoua-boulaï"]},
    "GET /inventories/{inventory_id}": None,
    "PUT /inventories/{inventory_id}/counts": lambda s: {
        "version": s.version(f"/inventories/{s.ids['inventory']}"),
        "counts": [{"article_id": s.ids["article"], "counted": "0"}]},
    "POST /inventories/{inventory_id}/validate": versioned(
        "/inventories/{inventory_id}", global_reason="comptage"),
    "POST /inventories/{inventory_id}/abandon": versioned("/inventories/{inventory_id}"),
}  # fmt: skip


def _member_version(side: Side) -> int:
    members = side.ok("GET", "/members", side.owner)
    items = members["items"] if isinstance(members, dict) else members
    return int(next(m["version"] for m in items if m["user_id"] == side.users["seller2"]))


ROUTES: Mapping[str, Body | None] = {**SHOP_ROUTES, **TRADE_ROUTES}
