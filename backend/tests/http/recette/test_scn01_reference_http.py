"""Critère A2 — SCN-01 (parcours CDC § 17.5, étapes du Lot 1) de bout en bout par HTTP.

Application complète, sur mémoire ou PostgreSQL (`--backend=postgres`). Attendu exact : coût
unitaire 540 000, ventes 780 000, encaissé 300 000, marge 240 000, créance 480 000, valeur du
stock 19 fois 540 000 ; le vendeur ne lit aucun coût ; le reçu porte « Vente à crédit ».
Achat reçu à Garoua (décision Q-01, specs § 15.1).
"""

from typing import Any

from app.domain.sales.ids import SaleId
from tests.http.recette.world import HJ, Side, open_shop
from tests.http.shops.conftest import Api

OWNER_COSTS = {"frozen_last_cost", "frozen_wac", "margin", "margin_wac"}


def _cdc_purchase_and_sale(api: Api) -> tuple[Side, dict[str, Any]]:
    side = open_shop(api, api.admin(), "Motos Garoua", "690000001", "6770000")
    owner, accountant, seller = side.owner, side.sessions["accountant"], side.sessions["seller"]
    article = side.ok("POST", "/articles", owner, json={**HJ, "base_price": 780_000})
    purchase = side.ok("POST", "/purchases", accountant, json={
        "lines": [{"article_id": article["id"], "quantity": "20", "unit_price": 520_000}],
        "fees": [{"kind": "customs", "amount": 400_000}], "location_id": side.ids["garoua"],
    })  # fmt: skip
    assert (purchase["number"], purchase["total"], purchase["payment_status"]) == (
        "A-000001", 10_800_000, "to_pay")  # fmt: skip
    [line] = purchase["lines"]
    assert (line["fee_share"], line["final_unit_cost"]) == (400_000, 540_000)
    modes = side.ok("GET", "/payment-modes", owner)
    cash = next(m["id"] for m in modes if m["name"] == "Espèces")
    sale = side.ok("POST", "/sales", seller, json={
        "id": str(SaleId.new()), "kind": "credit",
        "customer": {"name": "Moussa A.", "phone": "+237690000000", "kind": "individual"},
        "lines": [{"article_id": article["id"], "quantity": "1", "unit_price": 780_000}],
        "payments": [{"mode_id": cash, "amount": 300_000}],
    })  # fmt: skip
    return side, sale


def test_scn01_gives_exactly_the_cdc_figures(lot1: Api) -> None:
    side, sale = _cdc_purchase_and_sale(lot1)
    assert (sale["number"], sale["total"], sale["paid"], sale["remaining"]) == (
        "V-000001", 780_000, 300_000, 480_000)  # fmt: skip
    path = f"/sales/{sale['id']}"
    owner_line = side.ok("GET", path, side.owner)["lines"][0]
    assert {k: owner_line[k] for k in OWNER_COSTS} == {
        "frozen_last_cost": 540_000, "frozen_wac": 540_000, "margin": 240_000,
        "margin_wac": 240_000,
    }  # fmt: skip
    seller_line = side.ok("GET", path, side.sessions["seller"])["lines"][0]
    assert OWNER_COSTS & set(seller_line) == set()  # 7b, SEC-N01
    receivable = side.ok("GET", f"/receivables/{sale['receivable']['id']}", side.owner)
    assert (receivable["initial_amount"], receivable["status"]) == (480_000, "open")
    assert receivable["responsible_seller_id"] == side.users["seller"]
    today = side.ok("GET", "/dashboard", side.owner, params={"period": "today"})
    summary = today["summary"]
    assert {k: summary[k]["value"] for k in ("sales", "sales_count", "collected", "margin",
                                             "margin_wac")} == {
        "sales": 780_000, "sales_count": 1, "collected": 300_000, "margin": 240_000,
        "margin_wac": 240_000,
    }  # fmt: skip
    assert (summary["margin_rate_pct"], summary["without_cost"]) == ("30.77", 0)
    assert today["receivables"]["total_due"] == 480_000
    assert today["receivables"]["received"]["value"] == 0  # acompte exclu [Q-24]
    assert today["stock"]["value"]["at_wac"] == 19 * 540_000
    receipt = side.ok("GET", f"{path}/receipt", side.owner)
    assert "credit_sale" in [m["code"] for m in receipt["mentions"]]
    assert receipt["payments"] == [{"mode_name": "Espèces", "amount": 300_000, "reference": None}]
