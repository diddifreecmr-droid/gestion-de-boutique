"""Coûts et marges du gérant (`GET /dashboard/margins`, specs § 15.1, 2026-11-15) : coûts figés à
la vente, vente annulée exclue, série jour par jour ; propriétaire seul (vendeur, comptable,
chauffeur : 403, aucun chiffre) ; `no-store` ; périodes mal formées : 400."""

from tests.http.reporting.conftest import Desk
from tests.http.reporting.scn09 import _sell, stocked, utc

PATH = "/dashboard/margins"


def test_owner_reads_margins_at_costs_frozen_at_sale(desk: Desk) -> None:
    article = stocked(desk)  # dernier coût 550 000
    desk.at(utc(9, 9))
    _sell(desk, article, 800_000, [("Espèces", 800_000)])
    desk.at(utc(10, 9))
    _sell(desk, article, 700_000, [("Espèces", 700_000)])
    cancelled = _sell(desk, article, 900_000, [("Espèces", 900_000)])
    desk.ok("POST", f"/sales/{cancelled}/cancel", desk.owner, json={"reason": "Doublon"})
    response = desk.call("GET", f"{PATH}?period=custom&from=2026-11-08&to=2026-11-10", desk.owner)
    assert response.status_code == 200, response.text
    assert response.headers["Cache-Control"] == "no-store"
    report = response.json()
    assert report["totals"] == {"revenue": 1_500_000, "cost": 1_100_000, "margin": 400_000,
                                "margin_rate": "26.67", "without_cost": 0}  # fmt: skip
    [line] = report["articles"]
    assert (line["article_id"], line["quantity"], line["stock_unit"]) == (article, "2", "UNIT")
    assert line["figures"]["margin"] == 400_000
    assert (line["per_meter"], line["per_roll"], report["fabrics"]) == (None, None, [])
    assert [(d["day"], d["revenue"], d["cost"], d["margin"]) for d in report["days"]] == [
        ("2026-11-08", 0, 0, 0),
        ("2026-11-09", 800_000, 550_000, 250_000),
        ("2026-11-10", 700_000, 550_000, 150_000),
    ]
    today = desk.ok("GET", PATH, desk.owner)
    assert (today["period"]["kind"], today["totals"]["margin"]) == ("today", 150_000)


def test_margins_never_reach_other_roles_and_bad_periods_fail(desk: Desk) -> None:
    for role in ("seller", "accountant", "driver"):
        denied = desk.call("GET", PATH, desk.staff(role))
        assert (denied.status_code, denied.json()["error"]["code"]) == (403, "FORBIDDEN")
        assert "margin" not in denied.text
    for query in ("period=custom", "period=decade", "period=today&from=2026-11-01"):
        assert desk.call("GET", f"{PATH}?{query}", desk.owner).status_code == 400, query
