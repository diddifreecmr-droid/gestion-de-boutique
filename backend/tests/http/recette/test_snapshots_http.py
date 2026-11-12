"""CAT-06 et CAT-09 (H5, RG-T13) : une vente garde le nom et le prix de base de l'article
**au moment de la vente**, même après un renommage ou un changement de prix."""

from tests.http.recette.world import World


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
