"""T29 par HTTP (EXC-L3-04, M3-05, ERR3-02) : réglage `employee_exchange_allowed` lu et écrit
par les réglages de la boutique (propriétaire seul) et exposé au profil ; l'employé échange sa
vente seulement si le réglage est actif (sinon 403), jamais celle d'un autre (404), et pas
au-delà du délai (422 `EXCHANGE_PERIOD_OVER`) ; le propriétaire dépasse le délai (201)."""

from datetime import date, timedelta
from typing import Any

from app.domain.sales.ids import SaleId, SaleReturnId
from tests.http.catalog.test_catalog_http import Shop
from tests.http.purchasing.test_purchasing_http import bought
from tests.http.sales.test_sales_http import cash_mode
from tests.http.sales.test_sales_returns_http import cash_body
from tests.http.shops.conftest import Api, Session

E2_PHONE = "677000009"


def second_seller(shop: Shop) -> Session:
    locations = shop.call("GET", "/locations", shop.owner).json()["items"]
    garoua = next(loc["id"] for loc in locations if loc["name"] == "Garoua")
    body = {"name": "E2", "phone": E2_PHONE, "role": "seller", "default_location_id": garoua}
    added = shop.call("POST", "/members", shop.owner, json=body)
    assert added.status_code == 201, added.text
    return shop.api.login(E2_PHONE, added.json()["temporary_pin"])


def set_settings(shop: Shop, **values: Any) -> dict[str, Any]:
    version = shop.call("GET", "/settings", shop.owner).json()["version"]
    patched = shop.call("PATCH", "/settings", shop.owner, json={"version": version, **values})
    assert patched.status_code == 200, patched.text
    return dict(patched.json())


def exchange(shop: Shop, who: Session, sale_id: str, article: dict[str, Any], mode: str) -> Any:
    body = {
        "id": str(SaleReturnId.new()),
        "lines": [{"line": 1, "quantity": "1"}],
        "reason": "autre taille",
        "exchange": {
            "mode_id": mode,
            "sale": {
                "id": str(SaleId.new()),
                "kind": "cash",
                "lines": [{"article_id": article["id"], "quantity": "1", "unit_price": 780_000}],
            },
        },
    }
    return shop.call("POST", f"/sales/{sale_id}/returns", who, json=body)


def sell(shop: Shop, who: Session, article: dict[str, Any], mode: str, **extra: Any) -> str:
    sold = shop.call("POST", "/sales", who, json=cash_body(article, mode, 780_000, **extra))
    assert sold.status_code == 201, sold.text
    return str(sold.json()["id"])


def test_setting_over_http(api: Api) -> None:
    shop, _, _ = bought(api)
    seller = shop.staff["seller"]
    settings = shop.call("GET", "/settings", shop.owner).json()
    assert settings["employee_exchange_allowed"] is False  # défaut (QC-4)
    assert shop.call("GET", "/profile", seller).json()["employee_exchange_allowed"] is False
    patch = {"version": settings["version"], "employee_exchange_allowed": True}
    assert shop.call("PATCH", "/settings", seller, json=patch).status_code == 403
    null = {"version": settings["version"], "employee_exchange_allowed": None}
    assert shop.call("PATCH", "/settings", shop.owner, json=null).status_code == 400
    changed = set_settings(shop, employee_exchange_allowed=True, exchange_days=7)
    assert (changed["employee_exchange_allowed"], changed["exchange_days"]) == (True, 7)
    profile = shop.call("GET", "/profile", seller).json()
    assert (profile["employee_exchange_allowed"], profile["exchange_days"]) == (True, 7)


def test_employee_exchange_rights_over_http(api: Api) -> None:  # EXC-L3-04, M3-05
    shop, article, _ = bought(api)
    seller, accountant, e2 = shop.staff["seller"], shop.staff["accountant"], second_seller(shop)
    mode = cash_mode(shop)
    mine, theirs = sell(shop, seller, article, mode), sell(shop, e2, article, mode)
    refused = exchange(shop, seller, mine, article, mode)
    assert refused.status_code == 403
    assert refused.json()["error"]["details"]["setting"] == "employee_exchange_allowed"
    set_settings(shop, employee_exchange_allowed=True)
    made = exchange(shop, seller, mine, article, mode)
    assert made.status_code == 201, made.text
    assert "margin" not in made.json()  # vendeur : ni coût ni marge
    assert exchange(shop, seller, theirs, article, mode).status_code == 404
    assert exchange(shop, accountant, theirs, article, mode).status_code == 403
    assert exchange(shop, shop.owner, theirs, article, mode).status_code == 201


def test_period_over_http(api: Api) -> None:  # ERR3-02, EXC-L3-03
    shop, article, _ = bought(api)
    seller = shop.staff["seller"]
    set_settings(shop, employee_exchange_allowed=True, exchange_days=2)
    mode = cash_mode(shop)
    first = shop.call("GET", f"/sales/{sell(shop, seller, article, mode)}", seller).json()
    sold_on = date.fromisoformat(first["sold_on"]) - timedelta(days=3)
    old = sell(shop, seller, article, mode, sold_on=sold_on.isoformat())
    late = exchange(shop, seller, old, article, mode)
    assert late.status_code == 422, late.text
    error = late.json()["error"]
    assert error["code"] == "EXCHANGE_PERIOD_OVER"
    assert (error["details"]["sold_on"], error["details"]["exchange_days"]) == (
        sold_on.isoformat(),
        2,
    )
    assert exchange(shop, shop.owner, old, article, mode).status_code == 201
