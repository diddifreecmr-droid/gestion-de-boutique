"""Routes du stock : droits (M07 à M09), non-fuite des coûts (SEC-N01, SEC-N02), inventaire
masqué (INV-01), erreurs (ERR-STK-04, ADJ-02, INV-03, INV-05), idempotence par `id` client."""

from typing import Any

from app.domain.stock.ids import AdjustmentId
from tests.http.catalog.test_catalog_http import COST_WORDS, HJ, Shop, _keys
from tests.http.shops.conftest import Api


def leaked(body: object) -> list[str]:
    return [key for key in _keys(body) if any(word in key for word in COST_WORDS)]


def stocked(api: Api) -> tuple[Shop, dict[str, Any], dict[str, str]]:
    shop = Shop(api)
    article = shop.call("POST", "/articles", shop.owner, json={**HJ, "base_price": 780_000}).json()
    locations = shop.call("GET", "/locations", shop.owner).json()["items"]
    ids = {loc["name"]: loc["id"] for loc in locations}
    body = {
        "location_id": ids["Garoua"],
        "article_id": article["id"],
        "direction": "in",
        "quantity": "2",
        "reason": "entry_error",
    }
    added = shop.call("POST", "/adjustments", shop.owner, json=body)
    assert added.status_code == 201, added.text
    assert added.json()["balance_after"] == "2"
    return shop, article, ids


def test_matrix_by_role_without_cost_leak(api: Api) -> None:
    shop, article, ids = stocked(api)
    seller = shop.call("GET", "/stock", shop.staff["seller"])
    assert seller.status_code == 200
    body = seller.json()
    assert leaked(body) == []  # STK-02 / SEC-N01
    row = body["items"][0]
    assert (row["article_id"], row["total"], row["base_price"]) == (article["id"], "2", 780_000)
    garoua = next(cell for cell in row["cells"] if cell["location_id"] == ids["Garoua"])
    assert (garoua["sellable"], row["incoming"], row["stock_status"]) == (
        "2",
        "0",
        "ok",
    )  # seuil 2 : pas « sous »
    accountant = shop.call("GET", "/stock?q=hao&sort=quantity_desc", shop.staff["accountant"])
    row = accountant.json()["items"][0]
    assert "base_price" not in row
    assert (row["wac"], row["wac_value"], row["last_cost"]) == (None, None, None)
    only = shop.call("GET", f"/stock?location_id={ids['Garoua']}", shop.owner).json()
    assert [col["name"] for col in only["locations"]] == ["Garoua"]
    assert shop.call("GET", "/stock", shop.staff["driver"]).status_code == 403
    assert shop.call("GET", "/stock?sort=nope", shop.owner).status_code == 400


def test_value_damaged_history_and_rights(api: Api) -> None:
    shop, article, _ = stocked(api)
    for path in ("/stock/value", "/stock/damaged", f"/articles/{article['id']}/movements"):
        assert shop.call("GET", path, shop.staff["seller"]).status_code == 403  # M08
        assert shop.call("GET", path, shop.staff["accountant"]).status_code == 200
    value = shop.call("GET", "/stock/value", shop.owner).json()
    assert (value["sellable"]["at_wac"], value["sellable"]["without_wac"]) == (None, 1)
    assert value["damaged"]["at_wac"] == 0
    assert shop.call("GET", "/stock/damaged", shop.owner).json() == {"items": []}
    history = shop.call("GET", f"/articles/{article['id']}/movements", shop.owner).json()
    move = history["items"][0]
    assert (move["type"], move["type_label"], move["quantity"]) == (
        "adjustment_in",
        "Ajustement +",
        "2",
    )
    assert (move["balance_after"], move["document"]["type"]) == ("2", "adjustment")
    assert "unit_cost" in move
    assert history["next_cursor"] is None


def test_adjustment_errors_and_idempotence(api: Api) -> None:
    shop, article, ids = stocked(api)
    accountant = shop.staff["accountant"]
    body = {
        "location_id": ids["Garoua"],
        "article_id": article["id"],
        "direction": "out",
        "quantity": "3",
        "reason": "breakage",
    }
    refused = shop.call("POST", "/adjustments", accountant, json=body)
    assert refused.status_code == 422  # ERR-STK-04
    error = refused.json()["error"]
    assert (error["code"], error["details"]["available"]) == ("STOCK_INSUFFICIENT", "2")
    assert leaked(error) == []
    for broken in ({"quantity": "1.5"}, {"quantity": "0"}, {"reason": "other"}):
        assert shop.call("POST", "/adjustments", accountant, json=body | broken).status_code == 400
    wanted = str(AdjustmentId.new())
    once = body | {"quantity": "1", "id": wanted}
    assert shop.call("POST", "/adjustments", accountant, json=once).status_code == 201
    replay = shop.call("POST", "/adjustments", accountant, json=once)
    assert (replay.status_code, replay.json()["balance_after"]) == (200, None)
    assert shop.call("POST", "/adjustments", shop.staff["seller"], json=once).status_code == 403


def test_inventory_flow_hides_theoretical_until_validation(api: Api) -> None:
    shop, article, ids = stocked(api)
    accountant = shop.staff["accountant"]
    started = shop.call("POST", "/inventories", accountant, json={"location_id": ids["Garoua"]})
    assert started.status_code == 201, started.text
    inventory = started.json()
    assert (inventory["number"], inventory["status"]) == ("INV-000001", "in_progress")
    assert "theoretical" not in _keys(inventory)  # INV-01
    again = shop.call("POST", "/inventories", shop.owner, json={"location_id": ids["Garoua"]})
    assert again.json()["error"]["code"] == "INVENTORY_IN_PROGRESS"  # INV-05
    path = f"/inventories/{inventory['id']}"
    counts = {"version": 1, "counts": [{"article_id": article["id"], "counted": "1"}]}
    counted = shop.call("PUT", f"{path}/counts", accountant, json=counts).json()
    assert (counted["counted_lines"], counted["lines"][0]["counted"]) == (1, "1")
    assert "theoretical" not in _keys(shop.call("GET", path, shop.owner).json())
    missing = shop.call("POST", f"{path}/validate", accountant, json={"version": 2})
    assert missing.status_code == 400  # INV-03 : motif obligatoire
    assert missing.json()["error"]["details"]["articles"] == [article["id"]]
    reasons = {"version": 2, "reasons": [{"article_id": article["id"], "reason": "Casse"}]}
    done = shop.call("POST", f"{path}/validate", accountant, json=reasons).json()
    line = done["lines"][0]
    assert (line["theoretical"], line["difference"], line["gap_value"]) == ("2", "-1", None)
    assert (done["status"], done["gap_count"], done["gap_value"]) == ("validated", 1, None)
    assert shop.call("GET", path, shop.staff["seller"]).status_code == 403
    second = shop.call("POST", "/inventories", shop.owner, json={"location_id": ids["Garoua"]})
    abandon = shop.call(
        "POST", f"/inventories/{second.json()['id']}/abandon", shop.owner, json={"version": 1}
    )
    assert abandon.json()["status"] == "abandoned"
    stock = shop.call("GET", "/stock", shop.owner).json()["items"][0]
    assert stock["total"] == "1"
