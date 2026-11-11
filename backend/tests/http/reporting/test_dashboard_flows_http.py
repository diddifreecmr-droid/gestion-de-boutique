"""Indicateurs § 14.1 par HTTP hors SCN-09 : annulation un autre jour (Q-09), retour remboursé
(Q-05), versement annulé, créance ancienne (hors ventes, versements dans l'encaissé), vente sans
coût connu (SCN-10, RG-T15), alertes en attente, période « mois dernier »."""

from typing import Any

from app.domain.receivables.ids import ReceivableId
from app.domain.sales.ids import PriceRequestId, SaleReturnId
from tests.http.reporting.conftest import Desk
from tests.http.reporting.scn09 import _sell, stocked, utc
from tests.http.reporting.test_scn09_http import figures

D10 = "period=custom&from=2026-11-10&to=2026-11-10"


def _legacy(desk: Desk) -> str:
    body = {
        "id": str(ReceivableId.new()),
        "customer": {"id": None, "name": "Ali B.", "phone": "+237699000001"},
        "amount": 300_000,
        "opened_on": "2026-11-05",
        "description": "Cahier 2026",
    }
    return str(desk.ok("POST", "/receivables", desk.owner, json=body)["id"])


def _without_cost_sale(desk: Desk) -> str:
    """SCN-10 : article sans achat, ajustement +2 (coût d'entrée inconnu), vente à 900 000."""
    body = {"fields": {"brand": "Tricycle", "model": "T1", "engine_cc": 200}}
    article = str(desk.ok("POST", "/articles", desk.owner, json=body)["id"])
    places = desk.ok("GET", "/locations", desk.owner)["items"]
    garoua = next(p["id"] for p in places if p["name"] == "Garoua")
    adjust = {"location_id": garoua, "article_id": article, "direction": "in",
              "quantity": "2", "reason": "entry_error"}  # fmt: skip
    desk.ok("POST", "/adjustments", desk.owner, json=adjust)
    return _sell(desk, article, 900_000, [("Espèces", 900_000)])


def _price_request(desk: Desk, article: str) -> None:
    settings = desk.ok("GET", "/settings", desk.owner)
    desk.ok("PATCH", "/settings", desk.owner,
            json={"version": settings["version"], "min_price_enabled": True})  # fmt: skip
    version = desk.ok("GET", f"/articles/{article}", desk.owner)["version"]
    prices = {"version": version, "base_price": 780_000, "min_price": 720_000}
    desk.ok("PUT", f"/articles/{article}/prices", desk.owner, json=prices)
    ask = {"id": str(PriceRequestId.new()), "article_id": article, "requested_price": 700_000}
    desk.ok("POST", "/price-requests", desk.staff("seller"), json=ask)


def test_cancellation_return_refund_and_installments_count_on_their_day(desk: Desk) -> None:
    article = stocked(desk)
    ca = _legacy(desk)
    desk.at(utc(10, 9))
    first = _sell(desk, article, 800_000, [("Espèces", 800_000)])
    second = _sell(desk, article, 700_000, [("Espèces", 700_000)])
    paid = desk.ok("POST", f"/receivables/{ca}/installments", desk.owner,
                   json={"amount": 50_000, "mode_id": desk.mode("Espèces")})  # fmt: skip
    day10 = {"sales": 1_500_000, "sales_count": 2, "collected": 1_550_000, "margin": 400_000}
    before = figures(desk.ok("GET", "/dashboard", desk.owner))
    assert {k: before[k] for k in day10} == day10
    desk.at(utc(11, 9))
    desk.ok("POST", f"/sales/{second}/cancel", desk.owner, json={"reason": "Erreur"})
    back: dict[str, Any] = {
        "id": str(SaleReturnId.new()),
        "lines": [{"line": 1, "quantity": "1"}],
        "reason": "Moteur bruyant",
        "refund": {"amount": 800_000, "mode_id": desk.mode("Espèces")},
    }
    desk.ok("POST", f"/sales/{first}/returns", desk.owner, json=back)
    installment = paid["installment"]["id"]
    desk.ok("POST", f"/installments/{installment}/cancel", desk.owner, json={"reason": "Chèque"})
    _without_cost_sale(desk)
    today = desk.ok("GET", "/dashboard", desk.owner)
    assert figures(today) | {"rate": None} == {
        "sales": 900_000 - 700_000 - 800_000,
        "sales_count": 1 - 1,
        "collected": 900_000 - 700_000 - 800_000 - 50_000,
        "margin": -150_000 - 250_000,
        "margin_wac": -170_000 - 270_000,
        "expenses": 0,
        "result": -400_000,
        "rate": None,
        "gap": -40_000,
        "without_cost": 1,
    }
    assert today["receivables"]["received"] == {"value": -50_000, "previous": 50_000,
                                                 "change_pct": "-200.00"}  # fmt: skip
    assert today["receivables"]["total_due"] == 300_000
    unchanged = figures(desk.ok("GET", f"/dashboard?{D10}", desk.owner))
    assert {k: unchanged[k] for k in day10} == day10  # une journée passée ne bouge jamais
    sales = desk.ok("GET", "/dashboard/details/sales", desk.owner)
    assert sorted((line["kind"], line["amount"], line["margin"]) for line in sales["lines"]) == [
        ("cancellation", -700_000, -150_000),
        ("return", -800_000, -250_000),
        ("sale", 900_000, None),
    ]


def test_pending_alerts_and_last_month(desk: Desk) -> None:
    article = stocked(desk)
    desk.at(utc(10, 9))
    sale = _sell(desk, article, 800_000, [("Espèces", 800_000)])
    report = {"description": "Mauvais prix"}
    desk.ok("POST", f"/sales/{sale}/error-reports", desk.staff("seller"), json=report)
    _price_request(desk, article)
    alerts = desk.ok("GET", "/dashboard", desk.owner)["alerts"]
    assert alerts == {"error_reports": 1, "price_requests": 1}
    desk.at(utc(10, 9, 31))  # demande échue (30 min) : plus en attente
    assert desk.ok("GET", "/dashboard", desk.owner)["alerts"]["price_requests"] == 0
    desk.at(utc(30, 23, 30))  # 1er décembre à Douala
    last = desk.ok("GET", "/dashboard?period=last_month", desk.owner)
    assert (last["period"]["first_day"], last["period"]["last_day"]) == ("2026-11-01", "2026-11-30")
    assert last["period"]["days"] == 30
    assert figures(last)["sales"] == 800_000
    assert len(last["series"]["points"]) == 30
    assert last["series"]["average_sales"] == 26_667  # 800 000 / 30, demi vers le haut
    month = desk.ok("GET", "/dashboard?period=month", desk.owner)
    assert month["period"]["first_day"] == month["period"]["last_day"] == "2026-12-01"
