"""RG-T05 et RG-M01 par HTTP (critère A8 hors concurrence ; ERR-DUP-01 à 03, SEC-I08).

Numérotation : un refus ne consomme aucun numéro, un document annulé garde le sien, chaque
type et chaque boutique a sa séquence. Châssis : unique parmi les ventes **valides** de la
boutique, sans tenir compte des majuscules, des espaces ni de la ponctuation [Q-33].
La concurrence (20 ventes simultanées) est prouvée sur PostgreSQL :
`tests/infrastructure/postgres/test_sales_numbering.py`.
"""

from typing import Any

import pytest

from tests.http.recette.routes_trade import cash_sale
from tests.http.recette.world import Side, World


def chassis_sale(side: Side, *chassis: str) -> dict[str, Any]:
    body = cash_sale(side)
    price = body["lines"][0]["unit_price"]
    body["lines"][0].update(quantity=str(len(chassis)),
                            details=[{"chassis_number": c} for c in chassis])  # fmt: skip
    body["payments"][0]["amount"] = price * len(chassis)
    return body


def test_refusals_consume_no_number_and_cancelled_documents_keep_theirs(world: World) -> None:
    side, seller = world.a, world.a.sessions["seller"]
    short = cash_sale(side)
    short["lines"][0]["quantity"] = "30"
    short["payments"][0]["amount"] *= 30
    assert side.call("POST", "/sales", seller, json=short).status_code == 422
    assert side.ok("POST", "/sales", seller, json=cash_sale(side))["number"] == "V-000003"
    cancelled = side.ok("POST", f"/sales/{side.ids['sale_seller2']}/cancel", side.owner,
                        json={"reason": "client a renoncé"})  # fmt: skip
    assert (cancelled["number"], cancelled["status"]) == ("V-000002", "cancelled")
    assert side.ok("POST", "/sales", seller, json=cash_sale(side))["number"] == "V-000004"
    listed = [s["number"] for s in side.ok("GET", "/sales", side.owner)["items"]]
    assert sorted(listed) == ["V-000001", "V-000002", "V-000003", "V-000004"]  # aucun trou
    paid = side.ok("POST", f"/receivables/{side.ids['receivable_seller']}/installments", seller,
                   json={"amount": 1_000, "mode_id": side.ids["cash"]})  # fmt: skip
    assert paid["installment"]["number"] == "R-000002"  # séquence propre aux versements
    expense = side.ok("POST", "/expenses", side.owner,
                      json={"amount": 1_000, "category_id": side.ids["fuel"]})  # fmt: skip
    assert expense["number"] == "D-000003"  # 2 dépenses dans le jeu
    assert world.b.ok("POST", "/sales", world.b.owner, json=cash_sale(world.b))["number"] == (
        "V-000003")  # fmt: skip


@pytest.mark.parametrize("variant", ["LBX123", "lbx123", "LBX 123", "LBX123 ", "lbx-123"])
def test_a_sold_chassis_cannot_be_sold_again_in_any_spelling(world: World, variant: str) -> None:
    side = world.a  # LBX123 est déjà vendu sur V-000001 (vente valide)
    refused = side.call("POST", "/sales", side.owner, json=chassis_sale(side, variant))
    error = refused.json()["error"]
    assert (refused.status_code, error["code"]) == (409, "DUPLICATE")  # ERR-DUP-01, 02
    assert error["details"]["sale_number"] == "V-000001"


def test_same_chassis_twice_in_one_sale_and_scope_of_uniqueness(world: World) -> None:
    a, b = world.a, world.b
    twice = a.call("POST", "/sales", a.owner, json=chassis_sale(a, "NEW1", "new 1"))
    assert (twice.status_code, twice.json()["error"]["code"]) == (409, "DUPLICATE")  # ERR-DUP-03
    assert a.call("POST", "/sales", a.owner, json=chassis_sale(a, "ZZA1")).status_code == 201
    assert b.call("POST", "/sales", b.owner, json=chassis_sale(b, "ZZA1")).status_code == 201
    a.ok("POST", f"/sales/{a.ids['sale_seller']}/cancel", a.owner, json={"reason": "erreur"})
    again = a.ok("POST", "/sales", a.owner, json=chassis_sale(a, "LBX123"))  # libéré (RG-M01)
    assert again["number"] == "V-000004"
