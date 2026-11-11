"""`GET /offline-snapshot` (droit activé) : contenu par rôle, **aucun coût** pour personne
(SEC-N01), clients du vendeur seulement (Q-20), instantané complet (`since` renvoyé)."""

from typing import Any

from tests.http.sales.test_sales_http import leaked
from tests.http.sync.conftest import Desk


def test_snapshot_by_role_without_any_cost(desk: Desk) -> None:
    desk.enable()
    owner, seller = desk.shop.owner, desk.staff("seller")
    customer = {"name": "Awa", "phone": "+237690000011", "kind": "individual"}
    desk.ok("POST", "/customers", owner, json=customer)
    mine = {"name": "Ali", "phone": "+237690000012", "kind": "individual"}
    desk.ok("POST", "/customers", seller, json=mine)
    snapshots: dict[str, Any] = {
        role: desk.ok("GET", "/offline-snapshot?since=2026-11-01T00:00:00Z", who)
        for role, who in [("owner", owner), *desk.shop.staff.items()]
    }
    for body in snapshots.values():
        assert leaked(body) == []
        assert body["full"] is True
        assert body["since"].startswith("2026-11-01")
    seller_view = snapshots["seller"]
    [article] = seller_view["articles"]
    assert (article["display_name"], article["base_price"], article["min_price"]) == (
        "Haojue HJ125-8",
        780_000,
        720_000,
    )
    assert seller_view["min_price_enabled"] is True
    assert [c["name"] for c in seller_view["customers"]] == ["Ali"]
    assert seller_view["expense_categories"] == []
    assert {c["name"] for c in snapshots["owner"]["customers"]} == {"Ali", "Awa"}
    accountant = snapshots["accountant"]
    assert accountant["articles"] == []
    assert accountant["customers"] == []
    assert "Carburant" in [c["name"] for c in accountant["expense_categories"]]
    assert {m["name"] for m in accountant["payment_modes"]} >= {"Espèces"}
    driver = snapshots["driver"]
    assert driver["locations"] == []
    assert driver["articles"] == []
