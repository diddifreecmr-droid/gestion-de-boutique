"""Routes T16b : demandes de prix (ERR-PRM-05, M17) et retours (M14, SCN-05) par HTTP — codes,
droits (vendeur, comptable, chauffeur), idempotence, non-fuite des coûts pour le vendeur."""

from typing import Any

from app.domain.sales.ids import PriceRequestId, SaleId, SaleReturnId
from tests.http.catalog.test_catalog_http import Shop
from tests.http.purchasing.test_purchasing_http import bought
from tests.http.sales.test_sales_http import cash_mode, leaked
from tests.http.shops.conftest import Api


def minimum(shop: Shop, article: dict[str, Any], *, approval: bool = True) -> None:
    """Minimum 720 000 actif ; `approval` : accord du propriétaire exigé (faux par défaut)."""
    settings = shop.call("GET", "/settings", shop.owner).json()
    assert settings["min_price_requires_approval"] is False  # défaut (décision client)
    patch = {
        "version": settings["version"],
        "min_price_enabled": True,
        "min_price_requires_approval": approval,
    }
    assert shop.call("PATCH", "/settings", shop.owner, json=patch).status_code == 200
    path = f"/articles/{article['id']}"
    version = shop.call("GET", path, shop.owner).json()["version"]
    body = {"version": version, "base_price": 780_000, "min_price": 720_000}
    assert shop.call("PUT", f"{path}/prices", shop.owner, json=body).status_code == 200


def cash_body(article: dict[str, Any], mode: str, price: int, **extra: Any) -> dict[str, Any]:
    return {
        "id": str(SaleId.new()),
        "kind": "cash",
        "lines": [{"article_id": article["id"], "quantity": "1", "unit_price": price}],
        "payments": [{"mode_id": mode, "amount": price}],
        **extra,
    }


def test_price_request_flow_over_http(api: Api) -> None:
    shop, article, _ = bought(api)
    minimum(shop, article)
    seller, accountant = shop.staff["seller"], shop.staff["accountant"]
    rid = str(PriceRequestId.new())
    body = {"id": rid, "article_id": article["id"], "requested_price": 700_000}
    created = shop.call("POST", "/price-requests", seller, json=body)
    assert created.status_code == 201, created.text
    assert (created.json()["status"], created.json()["min_price"]) == ("pending", 720_000)
    assert shop.call("POST", "/price-requests", seller, json=body).status_code == 200
    assert shop.call("POST", "/price-requests", accountant, json=body).status_code == 403
    assert [r["id"] for r in shop.call("GET", "/price-requests", shop.owner).json()] == [rid]
    decision = f"/price-requests/{rid}/decision"
    accept = {"decision": "accept", "version": 1}
    assert shop.call("POST", decision, seller, json=accept).status_code == 403
    decided = shop.call("POST", decision, shop.owner, json=accept)
    assert decided.json()["status"] == "accepted"
    again = shop.call("POST", decision, shop.owner, json={"decision": "refuse"})
    assert again.json()["error"]["code"] == "INVALID_STATE_TRANSITION"
    mode = cash_mode(shop)
    refused = shop.call("POST", "/sales", seller, json=cash_body(article, mode, 700_000))
    assert refused.json()["error"]["details"]["request_required"] is True
    sale = cash_body(article, mode, 700_000, price_request_id=rid)
    sold = shop.call("POST", "/sales", seller, json=sale)
    assert sold.status_code == 201, sold.text
    linked = shop.call("GET", f"/price-requests/{rid}", seller).json()
    assert linked["sale_id"] == sold.json()["id"]
    assert shop.call("GET", f"/price-requests/{rid}", accountant).status_code == 403


def test_returns_over_http(api: Api) -> None:
    shop, article, _ = bought(api)
    seller, accountant = shop.staff["seller"], shop.staff["accountant"]
    mode = cash_mode(shop)
    sold = shop.call("POST", "/sales", seller, json=cash_body(article, mode, 780_000)).json()
    path = f"/sales/{sold['id']}/returns"
    body = {
        "id": str(SaleReturnId.new()),
        "lines": [{"line": 1, "quantity": "1", "condition": "damaged"}],
        "reason": "moteur bruyant",
        "refund": {"amount": 780_000, "mode_id": mode},
    }
    assert shop.call("POST", path, seller, json=body).status_code == 403
    made = shop.call("POST", path, shop.owner, json=body)
    assert made.status_code == 201, made.text
    returned = made.json()
    assert (returned["amount"], returned["margin"], returned["refund"]["amount"]) == (
        780_000,
        240_000,
        780_000,
    )
    assert returned["lines"][0]["condition"] == "damaged"
    assert shop.call("POST", path, shop.owner, json=body).status_code == 200  # rejeu
    more = {**body, "id": str(SaleReturnId.new()), "refund": None}
    exceeded = shop.call("POST", path, shop.owner, json=more)
    assert exceeded.json()["error"]["code"] == "RETURN_QUANTITY_EXCEEDED"
    assert exceeded.status_code == 422
    listing = shop.call("GET", path, seller)
    assert listing.status_code == 200
    assert listing.json()["balances"][0]["returnable"] == "0"
    assert leaked(listing.json()) == []  # vendeur : ni coût ni marge
    assert "margin" in shop.call("GET", path, shop.owner).json()["returns"][0]
    assert shop.call("GET", path, accountant).status_code == 403
    cancel = shop.call("POST", f"/sales/{sold['id']}/cancel", shop.owner, json={"reason": "x"})
    assert cancel.json()["error"]["code"] == "INVALID_STATE_TRANSITION"
