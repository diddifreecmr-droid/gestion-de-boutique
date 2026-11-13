"""Droits et non-fuite du Tableau de bord (M-lignes « Tableau de bord » et « Accueil », RG-D02,
RG-D03) : propriétaire seul pour `/dashboard` ; accueil par rôle sans marge ni coût pour le
vendeur, sans vente ni chiffre d'affaires pour le comptable ; autre boutique : 404 ; `no-store` ;
périodes mal formées : 400."""

from tests.http.catalog.test_catalog_http import _keys
from tests.http.reporting.conftest import Desk
from tests.http.reporting.scn09 import _sell, stocked, utc
from tests.http.sales.test_sales_http import leaked

SALES_WORDS = ("sale", "collected", "margin", "receivable", "result", "customer")


def test_dashboard_is_owner_only_and_other_shop_is_not_found(desk: Desk) -> None:
    for path in ("/dashboard", "/dashboard/details/sales", "/dashboard/details/low_stock"):
        response = desk.call("GET", path, desk.owner)
        assert response.status_code == 200, response.text
        assert response.headers["Cache-Control"] == "no-store"
        for role in ("seller", "accountant", "driver"):
            denied = desk.call("GET", path, desk.staff(role))
            assert (denied.status_code, denied.json()["error"]["code"]) == (403, "FORBIDDEN")
    other = desk.api.open_motos(desk.api.admin(), "690000009")
    stranger = desk.api.login("690000009", other["temporary_pin"])
    for path in ("/dashboard", "/home"):
        assert desk.api.call("GET", f"/shops/{desk.shop.id}{path}", stranger).status_code == 404


def test_homes_by_role_never_leak(desk: Desk) -> None:
    article = stocked(desk)
    desk.at(utc(10, 9))
    _sell(desk, article, 800_000, [("Espèces", 800_000)])
    seller = desk.call("GET", "/home", desk.staff("seller"))
    assert seller.headers["Cache-Control"] == "no-store"
    body = seller.json()
    assert set(body) == {"role", "today", "seller"}
    assert (body["role"], body["today"]) == ("seller", "2026-11-10")
    assert body["seller"] == {"sales_count": 1, "sales_amount": 800_000, "reminders_due": 0,
                              "pending_uploads": 0}  # fmt: skip
    assert leaked(body) == []  # aucune clé de coût, de marge ni de valeur (RG-D02)
    accountant = desk.ok("GET", "/home", desk.staff("accountant"))
    assert set(accountant) == {"role", "today", "accountant"}
    keys = _keys(accountant)
    assert not [k for k in keys if any(word in k for word in SALES_WORDS)]  # RG-D03
    block = accountant["accountant"]
    assert block["transfers_to_receive"] is None  # module à venir, jamais actif
    assert (block["low_stock"], block["expenses"]) == (0, 0)
    assert block["stock_value"]["at_wac"] == 19 * 530_000
    driver = desk.ok("GET", "/home", desk.staff("driver"))
    assert driver["driver"] == {"current_trip": None, "trip_expenses": None}
    owner = desk.ok("GET", "/home", desk.owner)
    assert set(owner) == {"role", "today", "owner"}
    assert owner["owner"]["summary"]["sales"]["value"] == 800_000


def test_low_stock_detail_and_bad_periods(desk: Desk) -> None:
    body = {"fields": {"brand": "Haojue", "model": "DR160", "engine_cc": 160}}
    desk.ok("POST", "/articles", desk.owner, json=body)
    low = desk.ok("GET", "/dashboard/details/low_stock", desk.owner)
    assert [(line["label"], line["quantity"], line["threshold"]) for line in low["lines"]] == [
        ("Haojue DR160", "0", "2")
    ]
    assert low["total"] == 1
    assert desk.ok("GET", "/dashboard", desk.owner)["stock"]["low_stock"] == 1
    for query in (
        "period=custom",
        "period=custom&from=2026-11-04",
        "period=today&from=2026-11-01",
        "period=custom&from=2026-11-05&to=2026-11-01",
        "period=custom&from=2026-11-01&to=2026-11-06",
        "period=custom&from=2024-01-01&to=2026-11-05",
        "period=decade",
    ):
        response = desk.call("GET", f"/dashboard?{query}", desk.owner)
        assert response.status_code == 400, (query, response.text)
    assert desk.call("GET", "/dashboard/details/unknown", desk.owner).status_code == 400
