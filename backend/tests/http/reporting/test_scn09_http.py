"""SCN-09 — Indicateurs § 14.1 sur une journée à cheval sur minuit UTC / Douala (recette § 2).

Journée testée D = mardi 10/11/2026. Valeurs attendues de la recette : ventes 2 310 000,
3 ventes, encaissé 1 850 000, marge 660 000, marge au CMP 720 000, taux 28,57 %, dépenses
25 000, résultat simple 635 000, total à recevoir 760 000, versements 100 000, valeur du stock
8 480 000 (dernier coût 8 800 000) ; bornes 22:59:59Z (le 10) et 23:00:00Z (le 11).
"""

from typing import Any

from tests.http.reporting.conftest import Desk
from tests.http.reporting.scn09 import record_s5, record_until_s4, utc

DAY_D = "period=custom&from=2026-11-10&to=2026-11-10"


def figures(body: dict[str, Any]) -> dict[str, Any]:
    s = body["summary"]
    keys = ("sales", "sales_count", "collected", "margin", "margin_wac", "expenses", "result")
    return {k: s[k]["value"] for k in keys} | {
        "rate": s["margin_rate_pct"],
        "gap": s["margin_gap"],
        "without_cost": s["without_cost"],
    }


DAY_D_FIGURES = {
    "sales": 2_310_000,
    "sales_count": 3,
    "collected": 1_850_000,
    "margin": 660_000,
    "margin_wac": 720_000,
    "expenses": 25_000,
    "result": 635_000,
    "rate": "28.57",
    "gap": 60_000,
    "without_cost": 0,
}


def test_day_straddling_midnight(desk: Desk) -> None:
    ids = record_until_s4(desk)
    desk.at(utc(10, 22, 59, 59))  # 23:59:59 à Douala : encore le 10
    today = desk.ok("GET", "/dashboard?period=today", desk.owner)
    assert today["period"]["first_day"] == "2026-11-10"
    assert figures(today) == DAY_D_FIGURES
    summary = today["summary"]
    assert summary["sales"] == {"value": 2_310_000, "previous": 800_000, "change_pct": "188.75"}
    assert summary["collected"]["change_pct"] == "131.25"
    assert summary["margin"] == {"value": 660_000, "previous": 250_000, "change_pct": "164.00"}
    assert summary["margin_wac"]["previous"] == 270_000
    assert today["series"] is None
    assert today["receivables"] == {
        "total_due": 760_000,
        "debtor_count": 2,
        "received": {"value": 100_000, "previous": 0, "change_pct": None},
        "reminders_due": 1,
    }
    stock = today["stock"]
    assert (stock["value"]["at_wac"], stock["value"]["at_last_cost"]) == (8_480_000, 8_800_000)
    assert (stock["low_stock"], stock["to_verify"]) == (0, 0)
    assert (stock["in_transit"], today["trucks"]) == (None, None)  # modules à venir
    assert today["alerts"] == {"error_reports": 0, "price_requests": 0}
    seller = desk.ok("GET", "/home", desk.staff("seller"))["seller"]
    assert seller == {"sales_count": 3, "sales_amount": 2_310_000, "reminders_due": 1,
                      "pending_uploads": 0}  # fmt: skip
    accountant = desk.ok("GET", "/home", desk.staff("accountant"))["accountant"]
    assert (accountant["expenses"], accountant["stock_value"]["at_wac"]) == (25_000, 8_480_000)
    payments = desk.ok("GET", f"/dashboard/details/payments?{DAY_D}", desk.owner)
    by_mode = {line["label"]: line["amount"] for line in payments["lines"]}
    assert by_mode == {"Espèces": 1_370_000, "Orange Money": 280_000, "MTN Mobile Money": 200_000}
    assert payments["total"] == 1_850_000
    expenses = desk.ok("GET", f"/dashboard/details/expenses?{DAY_D}", desk.owner)
    assert [(line["label"], line["amount"], line["count"]) for line in expenses["lines"]] == [
        ("Carburant", 25_000, 1)
    ]
    sales = desk.ok("GET", f"/dashboard/details/sales?{DAY_D}", desk.owner)
    assert sales["total"] == 2_310_000
    kinds = sorted((line["kind"], line["amount"]) for line in sales["lines"])
    assert kinds == [("cancellation", -790_000), ("sale", 760_000), ("sale", 770_000),
                     ("sale", 780_000), ("sale", 790_000)]  # fmt: skip
    owed = desk.ok("GET", "/dashboard/details/receivables", desk.owner)
    assert [line["amount"] for line in owed["lines"]] == [560_000, 200_000]
    assert owed["total"] == 760_000

    desk.at(utc(10, 23))  # minuit à Douala : nous sommes le 11, S5 n'existe pas encore
    after = desk.ok("GET", "/dashboard?period=today", desk.owner)
    assert (after["period"]["first_day"], figures(after)["sales"]) == ("2026-11-11", 0)
    assert after["summary"]["sales"]["previous"] == 2_310_000

    record_s5(desk, ids["article"])
    desk.at(utc(10, 23, 10))
    next_day = desk.ok("GET", "/dashboard?period=today", desk.owner)
    assert figures(next_day)["sales"] == 800_000
    assert next_day["summary"]["sales"]["change_pct"] == "-65.37"
    assert next_day["summary"]["margin"]["value"] == 250_000
    assert next_day["stock"]["value"]["at_wac"] == 15 * 530_000
    custom = desk.ok("GET", f"/dashboard?{DAY_D}", desk.owner)
    assert figures(custom) == DAY_D_FIGURES
    yesterday = desk.ok("GET", "/dashboard?period=yesterday", desk.owner)
    assert figures(yesterday) == DAY_D_FIGURES
    assert yesterday["summary"]["sales"]["previous"] == 800_000  # D-1 : S0 seule


def test_week_starts_on_monday(desk: Desk) -> None:
    ids = record_until_s4(desk)
    record_s5(desk, ids["article"])
    desk.at(utc(10, 11))  # mardi 10/11 12:00 à Douala
    week = desk.ok("GET", "/dashboard?period=week", desk.owner)
    assert (week["period"]["first_day"], week["period"]["last_day"]) == ("2026-11-09", "2026-11-10")
    f = figures(week)
    assert (f["sales"], f["sales_count"], f["margin"]) == (3_110_000, 4, 910_000)
    series = week["series"]
    assert [(p["day"], p["sales"], p["margin"]) for p in series["points"]] == [
        ("2026-11-09", 800_000, 250_000),
        ("2026-11-10", 2_310_000, 660_000),
    ]
    assert (series["average_sales"], series["average_margin"]) == (1_555_000, 455_000)
    assert week["previous_period"] == {"kind": "week", "first_day": "2026-11-07",
                                       "last_day": "2026-11-08", "days": 2}  # fmt: skip
