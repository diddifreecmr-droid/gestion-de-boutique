"""CAT-06, CAT-09 (H5, RG-T13) et SEC-X03 : une vente garde le nom et le prix de base de
l'article **au moment de la vente** ; rien ne disparaît quand un vendeur est désactivé."""

from typing import Any

from tests.http.recette.world import Side, World


def test_sale_keeps_article_name_and_base_price_after_changes(world: World) -> None:
    side = world.a
    path = f"/articles/{side.ids['article']}"
    renamed = side.ok("PATCH", path, side.owner, json={
        "version": side.version(path), "reason": "nouveau nom",
        "fields": {"brand": "Haojue", "model": "HJ125-8 Plus", "engine_cc": 125},
    })  # fmt: skip
    assert renamed["display_name"] == "Haojue HJ125-8 Plus"
    side.ok("PUT", f"{path}/prices", side.owner,
            json={"version": side.version(path), "base_price": 800_000})  # fmt: skip
    for who in (side.owner, side.sessions["seller"]):
        [line] = side.ok("GET", f"/sales/{side.ids['sale_seller']}", who)["lines"]
        assert (line["article_name"], line["base_price"]) == ("Haojue HJ125-8", 780_000)
    receipt = side.ok("GET", f"/sales/{side.ids['sale_seller']}/receipt", side.owner)
    assert "Haojue HJ125-8 Plus" not in str(receipt)
    history = side.ok("GET", path, side.owner)["price_history"]
    changes = [(h["price_kind"], h["old_price"], h["new_price"]) for h in history]
    assert ("base_price", 780_000, 800_000) in changes  # CAT-08 : historique gardé


def _member(side: Side, user_id: str) -> dict[str, Any]:
    found = side.ok("GET", "/members", side.owner)
    items = found["items"] if isinstance(found, dict) else found
    member: dict[str, Any] = next(m for m in items if m["user_id"] == user_id)
    return member


def test_history_of_a_disabled_seller_stays_listed(world: World) -> None:
    side, seller_id = world.a, world.a.users["seller"]  # SEC-X03 (RG-D06)
    version = _member(side, seller_id)["version"]
    side.ok("PATCH", f"/members/{seller_id}", side.owner,
            json={"version": version, "active": False})  # fmt: skip
    listed = side.ok("GET", "/sales", side.owner)["items"]
    assert side.ids["sale_seller"] in [s["id"] for s in listed]
    sale = side.ok("GET", f"/sales/{side.ids['sale_seller']}", side.owner)
    assert sale["seller_id"] == seller_id
    receivable = side.ok("GET", f"/receivables/{side.ids['receivable_seller']}", side.owner)
    assert [i["created_by"] for i in receivable["installments"]] == [seller_id]
    kept = _member(side, seller_id)
    assert (kept["active"], kept["name"]) == (False, "seller Motos Garoua")
