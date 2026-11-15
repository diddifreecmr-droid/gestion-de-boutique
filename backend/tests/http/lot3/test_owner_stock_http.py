"""Stock réservé au gérant, vente jamais refusée, rouleaux (décisions client du 2026-11-15).

- Prêt-à-porter et Textile : l'employé n'a plus les routes de stock (403) ; la liste des
  articles de la vente lui donne une pastille `ok` | `low` | `out` et **aucune quantité** ;
- la vente passe même sans stock : stock négatif, vente « à vérifier », alerte au gérant ;
- Textile : « 7 rouleaux + 12 m » dans le stock du gérant, reçu « 1 rouleau (30 m) » ;
- Prêt-à-porter : un nom suffit, aucun champ de vente.
"""

from typing import Any

from tests.http.attachments.conftest import MemoryBench
from tests.http.lot3.world import apparel_shop, keys_of, textile_shop

QUANTITY_KEYS = {"total", "sellable", "damaged", "incoming", "cells", "rolls", "meters_rest"}
QUANTITY_KEYS |= {"quantity", "available", "balance", "balance_after", "stock"}


def _line(article: dict[str, Any], quantity: str, price: int, **extra: str) -> dict[str, Any]:
    return {"article_id": article["id"], "quantity": quantity, "unit_price": price, **extra}


def test_seller_sees_badges_but_no_stock(bench: MemoryBench) -> None:
    for shop, unit in ((apparel_shop(bench), {}), (textile_shop(bench), {"unit": "METER"})):
        robe = shop.article({"name": "Robette avec sac", **unit}, base_price=9_000)
        sac = shop.article({"name": "Pantalon et boubou", **unit}, base_price=15_000)
        shop.buy(robe, "10", 5_000)
        shop.buy(sac, "1", 9_000)
        seller = shop.staff["seller"]
        for path in ("/stock", "/stock/damaged", f"/articles/{robe['id']}/movements"):
            assert shop.call("GET", path, seller).status_code == 403, path
        listed = shop.call("GET", "/articles", seller)
        assert listed.status_code == 200, listed.text
        badges = {i["display_name"]: i["stock_status"] for i in listed.json()["items"]}
        assert badges == {"Robette avec sac": "ok", "Pantalon et boubou": "low"}
        assert keys_of(listed.json()) & QUANTITY_KEYS == set()  # aucune quantité ne fuit
        assert shop.call("GET", "/stock", shop.owner).status_code == 200
        assert shop.call("GET", "/stock", shop.staff["accountant"]).status_code == 200


def test_sale_is_never_refused_and_flags_stock_to_verify(bench: MemoryBench) -> None:
    shop = apparel_shop(bench)
    robe = shop.article({"name": "Robette avec sac"}, base_price=9_000)
    sold = shop.sell(shop.staff["seller"], _line(robe, "2", 9_000))
    assert sold.status_code == 201, sold.text
    assert sold.json()["stock_to_verify"] is True
    row = shop.call("GET", "/stock", shop.owner).json()["items"][0]
    assert (row["total"], row["stock_status"]) == ("-2", "out")
    alerts = shop.call("GET", "/alerts", shop.owner).json()["items"]
    assert any(alert["type"] == "stock_to_verify" for alert in alerts)
    listed = shop.call("GET", "/articles", shop.staff["seller"]).json()["items"]
    assert listed[0]["stock_status"] == "out"


def test_rolls_in_owner_stock_and_receipt(bench: MemoryBench) -> None:
    shop = textile_shop(bench)
    fields = {"name": "Djampar — Rouge", "unit": "METER", "sold_by_piece": True}
    djampar = shop.article(fields | {"piece_length_m": "30"}, base_price=1_500)
    shop.buy(djampar, "222", 1_000)  # 7 rouleaux de 30 m + 12 m
    row = shop.call("GET", "/stock", shop.owner).json()["items"][0]
    assert (row["total"], row["rolls"], row["meters_rest"]) == ("222.0", 7, "12.0")
    line = _line(djampar, "1", 40_000, sale_mode="piece")
    sold = shop.sell(shop.staff["seller"], line)
    assert sold.status_code == 201, sold.text
    receipt = shop.call("GET", f"/sales/{sold.json()['id']}/receipt", shop.owner).json()
    assert receipt["lines"][0]["quantity_label"] == "1 rouleau (30 m)"
    profile = shop.call("GET", "/profile", shop.owner).json()
    assert (profile["piece_label"], profile["stock_reserved_to_owner"]) == ("rouleau", True)
    assert profile["refused_when_out_of_stock"] is False


def test_apparel_needs_only_a_name(bench: MemoryBench) -> None:
    shop = apparel_shop(bench)
    profile = shop.call("GET", "/profile", shop.staff["seller"]).json()
    assert profile["sale_fields"] == []
    assert [f["code"] for f in profile["article_fields"] if f["required"]] == ["name"]
    assert "stock" not in [entry["code"] for entry in profile["menu"]]
    created = shop.call("POST", "/articles", shop.owner, json={"fields": {"name": "Robette"}})
    assert created.status_code == 201, created.text
    assert created.json()["photo_id"] is None
    sized = _line(created.json(), "1", 0) | {"details": [{"size": "M"}]}
    assert shop.sell(shop.staff["seller"], sized).status_code == 400
