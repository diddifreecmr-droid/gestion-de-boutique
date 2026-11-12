"""SEC-I (critère A5) : la boutique A ne lit ni ne modifie jamais les données de B, par HTTP.

Balayages sur **toutes** les routes de `ROUTES` : la boutique B par un non-membre (son voisin
propriétaire de A, puis l'administrateur sans délégation) ; les objets de B par le chemin de
A. Puis références étrangères dans les corps, tableau de bord, rôle par boutique, unicité et
numérotation par boutique, alertes, journal et recherche par châssis.
"""

import json
import re
from typing import Any

from tests.http.recette.paths import url
from tests.http.recette.routes import ROUTES
from tests.http.recette.routes_trade import cash_sale
from tests.http.recette.world import Side, World

PARAM = re.compile(r"\{(\w+)\}")
SNAPSHOT = ("/articles/{article_id}", "/sales/{sale_id}", "/purchases/{purchase_id}",
            "/expenses/{expense_id}", "/receivables/{receivable_id}", "/settings",
            "/inventories/{inventory_id}")  # fmt: skip


def _send(target: Side, source: Side, route: str, who: Any) -> Any:
    """Requête sur la boutique `target`, chemin et corps remplis avec les objets de `source`."""
    method, template = route.split(" ", 1)
    factory = ROUTES[route]
    body = factory(source) if factory else None
    return target.api.call(method, f"/shops/{target.id}{url(source, template)}", who, json=body)


def _snapshot(side: Side) -> list[Any]:
    return [side.ok("GET", url(side, path), side.owner) for path in SNAPSHOT]


def test_shop_b_is_not_found_for_a_non_member_and_for_the_admin(world: World) -> None:
    before = _snapshot(world.b)
    for who in (world.a.owner, world.admin):  # NM et ADM sans délégation (specs § 8.3)
        gaps = [f"{r} : {s}" for r in ROUTES
                if (s := _send(world.b, world.b, r, who).status_code) != 404]  # fmt: skip
        assert gaps == []
    assert _snapshot(world.b) == before


def test_objects_of_b_are_not_found_through_shop_a(world: World) -> None:
    before = _snapshot(world.b)
    gaps = []
    for route in ROUTES:
        names = set(PARAM.findall(route)) - {"metric", "entity_type"}
        if not names:
            continue
        response = _send(world.a, world.b, route, world.a.owner)
        if route.startswith("GET /audit/"):  # lecture filtrée du journal de A : vide, jamais B
            ok = response.status_code == 200 and response.json()["items"] == []
        else:
            ok = response.status_code == 404
        gaps += [] if ok else [f"{route} : {response.status_code}"]
    assert gaps == []
    assert _snapshot(world.b) == before  # SEC-I05 : `version` de B identique


def test_references_to_objects_of_b_in_a_body_are_not_found(world: World) -> None:
    a, b = world.a, world.b
    stock_a, stock_b = (s.ok("GET", "/stock", s.owner) for s in (a, b))
    count = a.ok("GET", "/sales", a.owner)["totals"]["count"]
    sale = cash_sale(a)
    foreign = [
        {**sale, "lines": [{**sale["lines"][0], "article_id": b.ids["article"]}]},  # SEC-I03
        {**sale, "kind": "credit", "customer": {"id": b.ids["customer_seller"]}},  # SEC-I04
        {**sale, "payments": [{**sale["payments"][0], "mode_id": b.ids["cash"]}]},
        {**sale, "location_id": b.ids["garoua"]},
    ]  # fmt: skip
    for body in foreign:
        assert a.call("POST", "/sales", a.owner, json=body).status_code == 404, body
    others: dict[str, dict[str, Any]] = {
        "/purchases": {"lines": [{"article_id": b.ids["article"], "quantity": "1",
                                  "unit_price": 1_000}]},
        "/expenses": {"amount": 1_000, "category_id": b.ids["fuel"]},
        "/adjustments": {"location_id": b.ids["garoua"], "article_id": a.ids["article"],
                         "direction": "in", "quantity": "1", "reason": "entry_error"},
        "/inventories": {"location_id": b.ids["garoua"]},
    }  # fmt: skip
    for path, body in others.items():
        assert a.call("POST", path, a.owner, json=body).status_code == 404, path
    assert a.ok("GET", "/sales", a.owner)["totals"]["count"] == count  # aucune écriture
    assert [s.ok("GET", "/stock", s.owner) for s in (a, b)] == [stock_a, stock_b]


def test_dashboard_counts_only_its_own_shop(world: World) -> None:
    for side in (world.a, world.b):  # SEC-I06 : 2 ventes de 777 777 par boutique
        today = side.ok("GET", "/dashboard", side.owner, params={"period": "today"})
        assert "1555554" in json.dumps(today)
        assert "3111108" not in json.dumps(today)


def test_role_is_read_per_shop_at_each_request(world: World) -> None:
    a, b, u = world.a, world.b, world.u  # SEC-I07 : vendeur dans A, comptable dans B
    assert a.call("POST", "/sales", u, json=cash_sale(a)).status_code == 201
    assert b.call("POST", "/sales", u, json=cash_sale(b)).status_code == 403
    assert b.call("GET", "/stock/value", u).status_code == 200
    assert a.call("GET", "/stock/value", u).status_code == 403


def test_uniqueness_and_numbering_are_per_shop(world: World) -> None:
    for side in (world.a, world.b):  # SEC-I08 : téléphone, marque + modèle, châssis repris
        sale = side.ok("GET", f"/sales/{side.ids['sale_seller']}", side.owner)
        assert sale["number"] == "V-000001"  # SEC-I09
        assert sale["lines"][0]["details"][0]["chassis_number"] == "LBX123"
        purchase = side.ok("GET", f"/purchases/{side.ids['purchase']}", side.owner)
        expense = side.ok("GET", f"/expenses/{side.ids['expense']}", side.owner)
        inventory = side.ok("GET", f"/inventories/{side.ids['inventory']}", side.owner)
        assert (purchase["number"], expense["number"], inventory["number"]) == (
            "A-000001", "D-000001", "INV-000001")  # fmt: skip
    assert world.a.ids["article"] != world.b.ids["article"]
    assert world.a.ids["customer_seller"] != world.b.ids["customer_seller"]


def test_alerts_journal_and_chassis_search_stay_in_their_shop(world: World) -> None:
    a, b = world.a, world.b  # SEC-I10
    body = cash_sale(b)
    body["lines"][0]["details"] = [{"chassis_number": "ZZB999"}]
    b.ok("POST", "/sales", b.sessions["seller"], json=body)
    assert a.ok("GET", "/sales", a.owner, params={"q": "ZZB999"})["items"] == []
    assert b.ok("GET", "/sales", b.owner, params={"q": "ZZB999"})["items"] != []
    b_ids = set(b.ids.values()) | set(b.users.values()) | {b.id}
    text = json.dumps([a.ok("GET", "/audit", a.owner, params={"limit": 200}),
                       a.ok("GET", "/alerts", a.owner)])  # fmt: skip
    assert [i for i in b_ids if i in text] == []
