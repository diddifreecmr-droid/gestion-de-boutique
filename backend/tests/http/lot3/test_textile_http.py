"""T31 — textile par HTTP sur la boutique X de la recette : raccourcis RG-X05 (TEX-04), reçu
« 2,5 m » et « 1 pièce (5,49 m) » (TEX-06), longueur au dixième (TEX-01, ERR3-09), aucune clé
de coût pour l'employé (SEC-N3-01, sentinelle CMP 2 004), chute et ses droits (M3-08)."""

from typing import Any

from tests.http.attachments.conftest import MemoryBench
from tests.http.lot3.world import (
    WX_FIELDS,
    WX_PRICES,
    Lot3Shop,
    apparel_shop,
    keys_of,
    textile_shop,
)

LEAKS = ("cost", "wac", "margin", "value")


def _wax_shop(bench: MemoryBench) -> tuple[Lot3Shop, dict[str, Any]]:
    shop = textile_shop(bench)
    wax = shop.article(WX_FIELDS, **WX_PRICES)
    shop.buy(wax, "10", 11_000, unit="PIECE")  # 54,9 m, CMP 2 004
    return shop, wax


def _leaks(body: object) -> list[str]:
    return sorted(k for k in keys_of(body) if any(word in k for word in LEAKS))


def test_profile_serves_the_textile_shortcuts(bench: MemoryBench) -> None:
    shop = textile_shop(bench)
    served = shop.call("GET", "/profile", shop.staff["seller"]).json()["sale_shortcuts"]
    assert [(s["code"], s["label"], s["basis"]) for s in served] == [
        ("piece", "Pièce complète", "piece"),
        ("half_piece", "Demi-pièce", "half_piece"),
        ("1m", "1 m", "length"),
        ("2m", "2 m", "length"),
        ("3m", "3 m", "length"),
    ]
    assert [(s["length_m"], s["yards"]) for s in served] == [
        (None, "6"),
        (None, "3"),
        ("1", None),
        ("2", None),
        ("3", None),
    ]
    apparel = apparel_shop(bench)
    assert apparel.call("GET", "/profile", apparel.owner).json()["sale_shortcuts"] == []


def test_meter_and_piece_sale_receipt_without_costs(bench: MemoryBench) -> None:
    shop, wax = _wax_shop(bench)
    owner_view = shop.call("GET", f"/articles/{wax['id']}", shop.owner).json()
    assert owner_view["wac"] == 2_004  # la sentinelle existe
    seller = shop.staff["seller"]
    sold = shop.sell(
        seller,
        {"article_id": wax["id"], "sale_mode": "meter", "quantity": "2.5", "unit_price": 2_500},
        {"article_id": wax["id"], "sale_mode": "piece", "quantity": "1", "unit_price": 13_000},
    )
    assert sold.status_code == 201, sold.text
    sale = sold.json()
    assert (sale["total"], _leaks(sale)) == (19_250, [])
    receipt = shop.call("GET", f"/sales/{sale['id']}/receipt", seller)
    assert receipt.status_code == 200, receipt.text
    lines = receipt.json()["lines"]
    assert [(line["quantity_label"], line["unit_price"]) for line in lines] == [
        ("2,5 m", 2_500),
        ("1 pièce (5,49 m)", 13_000),
    ]
    assert _leaks(receipt.json()) == []
    listed = shop.call("GET", "/articles?with_thumbnails=true", seller).json()
    assert _leaks(listed) == []
    stock = shop.call("GET", "/stock", shop.owner).json()
    assert stock["items"][0]["total"] == "46.9"


def test_length_is_entered_to_the_tenth(bench: MemoryBench) -> None:
    shop, wax = _wax_shop(bench)
    seller = shop.staff["seller"]
    line = {"article_id": wax["id"], "sale_mode": "meter", "unit_price": 2_500}
    refused = shop.sell(seller, {**line, "quantity": "2.55"})
    assert refused.status_code == 400
    assert refused.json()["error"]["details"]["field"] == "lines.quantity"
    short = shop.sell(seller, {**line, "quantity": "60"})
    assert short.status_code == 422
    error = short.json()["error"]
    assert (error["code"], error["details"]["available"]) == ("STOCK_INSUFFICIENT", "54.9")


def test_offcut_with_photo_and_rights(bench: MemoryBench) -> None:
    shop, wax = _wax_shop(bench)
    photo = bench.upload(shop, shop.owner, owner_type="stock_adjustment", kind="photo")
    assert photo.status_code == 201, photo.text
    body = {
        "location_id": shop.store,
        "article_id": wax["id"],
        "direction": "out",
        "quantity": "0.4",
        "reason": "offcut",
        "note": "bout taché",
        "photo_id": photo.json()["id"],
    }
    assert shop.call("POST", "/adjustments", shop.staff["seller"], json=body).status_code == 403
    for who in (shop.owner, shop.staff["accountant"]):  # M3-08
        done = shop.call("POST", "/adjustments", who, json=body)
        assert done.status_code == 201, done.text
        assert (done.json()["reason"], done.json()["photo_id"]) == ("offcut", body["photo_id"])
    assert done.json()["balance_after"] == "54.1"
    inward = shop.call("POST", "/adjustments", shop.owner, json={**body, "direction": "in"})
    assert (inward.status_code, inward.json()["error"]["details"]["field"]) == (400, "direction")
    moves = shop.call("GET", f"/articles/{wax['id']}/movements", shop.owner).json()["items"]
    assert [m["type"] for m in moves[:2]] == ["offcut", "offcut"]
