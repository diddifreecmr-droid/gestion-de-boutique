"""Routes des achats et fournisseurs : droits (M10, M11), 404 entre boutiques (SEC-I),
idempotence par `id` client, avertissement de prix (PUR-02), erreurs (PUR-04, SCN-03 d,
ERR-OVR-05), correction (SCN-04) et paiements (PUR-12)."""

from typing import Any

from app.domain.purchasing.ids import PurchaseId, SupplierPaymentId
from tests.http.catalog.test_catalog_http import HJ, Shop
from tests.http.shops.conftest import Api


def bought(api: Api) -> tuple[Shop, dict[str, Any], dict[str, Any]]:
    shop = Shop(api)
    article = shop.call("POST", "/articles", shop.owner, json=HJ).json()
    body = {
        "id": str(PurchaseId.new()),
        "lines": [{"article_id": article["id"], "quantity": "20", "unit_price": 520_000}],
        "fees": [{"kind": "customs", "amount": 400_000}],
    }
    created = shop.call("POST", "/purchases", shop.staff["accountant"], json=body)
    assert created.status_code == 201, created.text
    return shop, article, created.json()


def test_scn01_over_http_with_idempotent_replay(api: Api) -> None:
    shop, article, purchase = bought(api)
    assert (purchase["number"], purchase["total"], purchase["payment_status"]) == (
        "A-000001",
        10_800_000,
        "to_pay",
    )
    [line] = purchase["lines"]
    assert (line["fee_share"], line["final_unit_cost"], line["stock_quantity"]) == (
        400_000,
        540_000,
        "20",
    )
    replay = {
        "id": purchase["id"],
        "lines": [{"article_id": article["id"], "quantity": "1", "unit_price": 1}],
    }
    again = shop.call("POST", "/purchases", shop.owner, json=replay)
    assert (again.status_code, again.json()["number"]) == (200, "A-000001")
    listing = shop.call("GET", "/purchases", shop.owner).json()
    assert (listing["totals"]["count"], listing["totals"]["total"]) == (1, 10_800_000)
    assert shop.call("GET", f"/purchases/{purchase['id']}", shop.owner).status_code == 200


def test_rights_seller_driver_and_cancel(api: Api) -> None:
    shop, _, purchase = bought(api)
    path = f"/purchases/{purchase['id']}"
    for role in ("seller", "driver"):
        who = shop.staff[role]
        for method, suffix in (("GET", "/purchases"), ("GET", path), ("GET", "/suppliers")):
            assert shop.call(method, suffix, who).status_code == 403  # M10
    cancel = {"reason": "doublon"}
    accountant = shop.call("POST", f"{path}/cancel", shop.staff["accountant"], json=cancel)
    assert accountant.status_code == 403  # M11 [Q-13]
    done = shop.call("POST", f"{path}/cancel", shop.owner, json=cancel)
    assert (done.status_code, done.json()["status"]) == (200, "cancelled")


def test_cross_shop_404_and_input_errors(api: Api) -> None:
    shop, article, purchase = bought(api)
    other = api.call("POST", "/platform/shops", api.admin(), json={
        "profile_code": "motos", "name": "Motos Ngaoundéré", "city": "Ngaoundéré",
        "phone": "222000001", "owner": {"name": "Moussa", "phone": "690000001"},
    })  # fmt: skip
    foreign = f"/shops/{other.json()['shop']['shop_id']}/purchases/{purchase['id']}"
    assert api.call("GET", foreign, shop.owner).status_code == 404
    line = {"article_id": article["id"], "unit_price": 520_000}
    for quantity in ("0", "-1", "1.5"):
        body = {"lines": [{**line, "quantity": quantity}]}
        assert shop.call("POST", "/purchases", shop.owner, json=body).status_code == 400
    other_fee = {"lines": [{**line, "quantity": "1"}], "fees": [{"kind": "other", "amount": 1}]}
    assert shop.call("POST", "/purchases", shop.owner, json=other_fee).status_code == 400
    gap = shop.call("POST", "/purchases", shop.owner,
                    json={"lines": [{**line, "quantity": "1", "unit_price": 52_000}]})  # fmt: skip
    assert gap.status_code == 422
    assert gap.json()["error"]["code"] == "PRICE_GAP_CONFIRMATION_REQUIRED"
    confirmed = {"lines": [{**line, "quantity": "1", "unit_price": 52_000}],
                 "confirm_price_gap": True}  # fmt: skip
    assert shop.call("POST", "/purchases", shop.owner, json=confirmed).status_code == 201


def test_correction_and_payments(api: Api) -> None:
    shop, article, purchase = bought(api)
    path = f"/purchases/{purchase['id']}"
    patch = {
        "version": purchase["version"],
        "reason": "faute de frappe",
        "lines": [{"article_id": article["id"], "quantity": "20", "unit_price": 530_000}],
        "invoice_ref": None,
    }
    fixed = shop.call("PATCH", path, shop.staff["accountant"], json=patch)
    assert fixed.status_code == 200, fixed.text
    assert (fixed.json()["total"], fixed.json()["version"]) == (11_000_000, 2)
    assert shop.call("PATCH", path, shop.owner, json=patch).status_code == 409
    no_reason = {"version": 2, "reason": " ", "note": "x"}
    assert shop.call("PATCH", path, shop.owner, json=no_reason).status_code == 400
    cleared = {"version": 2, "reason": "x", "lines": None}
    assert shop.call("PATCH", path, shop.owner, json=cleared).status_code == 400
    modes = shop.call("GET", "/payment-modes", shop.owner).json()
    pay = {"id": str(SupplierPaymentId.new()), "amount": 11_000_000, "mode_id": modes[0]["id"]}
    paid = shop.call("POST", f"{path}/payments", shop.staff["accountant"], json=pay)
    assert (paid.status_code, paid.json()["payment_status"]) == (201, "paid")
    assert shop.call("POST", f"{path}/payments", shop.owner, json=pay).status_code == 200
    more = {"amount": 1, "mode_id": modes[0]["id"]}
    over = shop.call("POST", f"{path}/payments", shop.owner, json=more)
    assert (over.status_code, over.json()["error"]["code"]) == (422, "OVERPAYMENT")


def test_suppliers_routes(api: Api) -> None:
    shop = Shop(api)
    accountant = shop.staff["accountant"]
    created = shop.call("POST", "/suppliers", accountant, json={"name": "Haojue Douala"})
    assert created.status_code == 201
    supplier = created.json()
    dup = shop.call("POST", "/suppliers", shop.owner, json={"name": "haojue douala"})
    assert (dup.status_code, dup.json()["error"]["code"]) == (409, "DUPLICATE")
    replay = {"id": supplier["id"], "name": "autre"}
    assert shop.call("POST", "/suppliers", shop.owner, json=replay).status_code == 200
    path = f"/suppliers/{supplier['id']}"
    off = shop.call("PATCH", path, shop.owner, json={"version": 1, "active": False})
    assert (off.status_code, off.json()["active"]) == (200, False)
    blank = shop.call("PATCH", path, shop.owner, json={"version": 2, "name": None})
    assert blank.status_code == 400
    sheet = shop.call("GET", f"{path}?from=2026-11-01&to=2026-11-30", shop.owner).json()
    assert (sheet["totals"]["total"], sheet["purchases"]) == (0, [])
    listed = shop.call("GET", "/suppliers", accountant).json()["items"]
    assert [s["name"] for s in listed] == ["Haojue Douala"]
    assert (
        shop.call("POST", "/suppliers", shop.staff["seller"], json={"name": "X"}).status_code == 403
    )
