"""Décisions client (specs § 15.1) par HTTP : prix minimum en avertissement par défaut
(`PRICE_APPROVAL_DISABLED` pour une demande), réglage exposé au profil, échange à crédit."""

from typing import Any

from app.domain.sales.ids import PriceRequestId, SaleId, SaleReturnId
from tests.http.catalog.test_catalog_http import Shop
from tests.http.purchasing.test_purchasing_http import bought
from tests.http.sales.test_sales_http import cash_mode
from tests.http.sales.test_sales_returns_http import cash_body, minimum
from tests.http.shops.conftest import Api


def test_below_minimum_is_a_warning_by_default(api: Api) -> None:
    shop, article, _ = bought(api)
    minimum(shop, article, approval=False)
    seller = shop.staff["seller"]
    profile = shop.call("GET", "/profile", seller).json()
    assert (profile["min_price_enabled"], profile["min_price_requires_approval"]) == (True, False)
    sold = shop.call("POST", "/sales", seller, json=cash_body(article, cash_mode(shop), 700_000))
    assert sold.status_code == 201, sold.text
    assert sold.json()["warnings"] == [
        {
            "code": "PRICE_BELOW_MINIMUM",
            "message": "Prix inférieur au minimum de 720 000 FCFA",
            "details": {"article_id": article["id"], "line": 1, "min_price": 720_000},
        }
    ]
    ask = {"id": str(PriceRequestId.new()), "article_id": article["id"], "requested_price": 1}
    refused = shop.call("POST", "/price-requests", seller, json=ask)
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "PRICE_APPROVAL_DISABLED"


def test_owner_turns_approval_on(api: Api) -> None:
    shop, article, _ = bought(api)
    minimum(shop, article, approval=True)
    settings = shop.call("GET", "/settings", shop.owner).json()
    assert settings["min_price_requires_approval"] is True
    seller = shop.staff["seller"]
    patch = {"version": settings["version"], "min_price_requires_approval": False}
    assert shop.call("PATCH", "/settings", seller, json=patch).status_code == 403
    sold = shop.call("POST", "/sales", seller, json=cash_body(article, cash_mode(shop), 700_000))
    assert sold.json()["error"]["details"]["request_required"] is True


def _exchange(shop: Shop, sale_id: str, article: dict[str, Any], mode: str) -> Any:
    body = {
        "id": str(SaleReturnId.new()),
        "lines": [{"line": 1, "quantity": "1"}],
        "reason": "change de modèle",
        "exchange": {
            "mode_id": mode,
            "sale": {
                "id": str(SaleId.new()),
                "kind": "credit",
                "lines": [{"article_id": article["id"], "quantity": "1", "unit_price": 900_000}],
            },
        },
    }
    return shop.call("POST", f"/sales/{sale_id}/returns", shop.owner, json=body)


def test_credit_exchange_over_http(api: Api) -> None:
    shop, article, _ = bought(api)
    mode = cash_mode(shop)
    customer = {"name": "Moussa A.", "phone": "+237690000000"}
    sale = cash_body(article, mode, 780_000, customer=customer)
    sold = shop.call("POST", "/sales", shop.staff["seller"], json=sale).json()
    made = _exchange(shop, sold["id"], article, mode)
    assert made.status_code == 201, made.text
    new = made.json()["exchange_sale"]
    assert (new["kind"], new["paid"], new["remaining"]) == ("credit", 780_000, 120_000)
    assert new["customer_id"] == sold["customer_id"] is not None
    anonymous = shop.call("POST", "/sales", shop.owner, json=cash_body(article, mode, 780_000))
    refused = _exchange(shop, anonymous.json()["id"], article, mode)
    assert refused.status_code == 400
    assert refused.json()["error"]["details"] == {"field": "customer"}
