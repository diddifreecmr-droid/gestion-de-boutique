"""Tissus textiles par HTTP (décision client du 2026-11-15) : un article par couleur.

Création « Djampar » rouge/bleu en une transaction, filtre `?fabric=`, tissu en double (409),
Getzner au mètre seulement, prix et longueur modifiés pour toutes les couleurs, ajout d'une
couleur qui reprend les prix, unicité du nom inchangée, droits (comptable sans prix, vendeur).
"""

from typing import Any

from tests.http.attachments.conftest import MemoryBench
from tests.http.lot3.world import Lot3Shop, apparel_shop, textile_shop

DJAMPAR = {
    "fabric": "Djampar",
    "colors": ["Rouge", "Bleu"],
    "base_price": 1_500,
    "base_price_piece": 40_000,
    "roll_length_m": "30",
    "alert_threshold": "60",
}


def _create(shop: Lot3Shop, body: dict[str, Any], who: Any = None) -> Any:
    return shop.call("POST", "/articles/fabrics", who or shop.owner, json=body)


def test_fabric_creates_one_article_per_color(bench: MemoryBench) -> None:
    shop = textile_shop(bench)
    created = _create(shop, DJAMPAR)
    assert created.status_code == 201, created.text
    items = created.json()["items"]
    assert created.json()["fabric"] == "Djampar"
    assert [i["display_name"] for i in items] == ["Djampar — Rouge", "Djampar — Bleu"]
    assert {(i["fabric"], i["attributes"]["color"]) for i in items} == {
        ("Djampar", "Rouge"),
        ("Djampar", "Bleu"),
    }
    assert {(i["stock_unit"], i["sold_by_piece"], i["piece_length_m"]) for i in items} == {
        ("METER", True, "30.00")
    }
    assert {(i["base_price"], i["base_price_piece"], i["alert_threshold"]) for i in items} == {
        (1_500, 40_000, "60.0")
    }
    listed = shop.call("GET", "/articles?fabric=djampar", shop.owner).json()["items"]
    assert [i["display_name"] for i in listed] == ["Djampar — Bleu", "Djampar — Rouge"]
    shop.article({"name": "Wax hollandais", "unit": "METER"})
    assert len(shop.call("GET", "/articles?fabric=Djampar", shop.owner).json()["items"]) == 2
    journal = shop.call("GET", "/audit", shop.owner).json()["items"]
    summaries = {entry["summary"] for entry in journal}
    assert {"Article créé : Djampar — Rouge", "Article créé : Djampar — Bleu"} <= summaries


def test_duplicate_fabric_or_color_is_refused_whole(bench: MemoryBench) -> None:
    shop = textile_shop(bench)
    assert _create(shop, DJAMPAR).status_code == 201
    again = _create(shop, DJAMPAR | {"colors": ["Vert"]})
    assert again.status_code == 409, again.text
    assert again.json()["error"]["details"]["constraint"] == "article_fabric"
    shop.article({"name": "Bazin — Blanc", "unit": "METER"})
    clash = _create(shop, {"fabric": "Bazin", "colors": ["Noir", "blanc"], "meter_only": True})
    assert clash.status_code == 409, clash.text  # unicité du nom inchangée
    assert shop.call("GET", "/articles?fabric=Bazin", shop.owner).json()["items"] == []
    twice = _create(shop, {"fabric": "Kente", "colors": ["Or", "or"], "meter_only": True})
    assert twice.status_code == 400, twice.text


def test_meter_only_fabric_needs_no_roll(bench: MemoryBench) -> None:
    shop = textile_shop(bench)
    getzner = {"fabric": "Getzner", "colors": ["Blanc"], "meter_only": True, "base_price": 9_000}
    created = _create(shop, getzner)
    assert created.status_code == 201, created.text
    assert created.json()["items"][0]["sold_by_piece"] is False
    no_roll = _create(shop, {"fabric": "Super wax", "colors": ["Jaune"]})
    assert no_roll.status_code == 400, no_roll.text  # longueur du rouleau exigée
    roll_price = getzner | {"fabric": "Getzner 2", "base_price_piece": 50_000}
    assert _create(shop, roll_price).status_code == 422


def test_fabric_update_applies_to_every_color(bench: MemoryBench) -> None:
    shop = textile_shop(bench)
    _create(shop, DJAMPAR)
    prices = {"base_price": 1_800, "base_price_piece": 45_000}
    patch = {"prices": prices, "roll_length_m": "25", "alert_threshold": "50"}
    updated = shop.call("PATCH", "/articles/fabrics/Djampar", shop.owner, json=patch)
    assert updated.status_code == 200, updated.text
    items = updated.json()["items"]
    assert len(items) == 2
    assert {(i["base_price"], i["base_price_piece"], i["piece_length_m"]) for i in items} == {
        (1_800, 45_000, "25.00")
    }
    assert {i["alert_threshold"] for i in items} == {"50.0"}
    meter = shop.call("PATCH", "/articles/fabrics/djampar", shop.owner, json={"meter_only": True})
    assert meter.status_code == 200, meter.text
    assert {(i["sold_by_piece"], i["base_price_piece"]) for i in meter.json()["items"]} == {
        (False, None)
    }
    missing = shop.call("PATCH", "/articles/fabrics/Inconnu", shop.owner, json={})
    assert missing.status_code == 404


def test_new_color_takes_the_fabric_terms(bench: MemoryBench) -> None:
    shop = textile_shop(bench)
    _create(shop, DJAMPAR)
    added = shop.call(
        "POST", "/articles/fabrics/DJAMPAR/colors", shop.owner, json={"colors": ["Vert"]}
    )
    assert added.status_code == 201, added.text
    new = next(i for i in added.json()["items"] if i["display_name"] == "Djampar — Vert")
    assert (new["fabric"], new["base_price"], new["base_price_piece"]) == ("Djampar", 1_500, 40_000)
    assert (new["piece_length_m"], new["alert_threshold"]) == ("30.00", "60.0")
    assert len(added.json()["items"]) == 3


def test_fabric_rights_and_profile(bench: MemoryBench) -> None:
    shop = textile_shop(bench)
    accountant, seller = shop.staff["accountant"], shop.staff["seller"]
    assert _create(shop, DJAMPAR, accountant).status_code == 403  # prix : propriétaire seul
    plain = {k: v for k, v in DJAMPAR.items() if "price" not in k}
    assert _create(shop, plain, accountant).status_code == 201
    assert _create(shop, plain | {"fabric": "Bogolan"}, seller).status_code == 403
    apparel = apparel_shop(bench)
    refused = _create(apparel, {"fabric": "Lin", "colors": ["Blanc"], "meter_only": True})
    assert refused.status_code == 400, refused.text
