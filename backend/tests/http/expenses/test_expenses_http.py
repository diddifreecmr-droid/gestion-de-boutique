"""Routes des dépenses (EXP-01/03/05/06, M23, M24, AUD-07) : statuts, droits, idempotence."""

from datetime import UTC, datetime, timedelta
from typing import Any

from app.domain.expenses.ids import ExpenseId
from tests.application.identity.support import T0
from tests.http.expenses.conftest import ExpenseShop


def fuel(shop: ExpenseShop, **extra: Any) -> dict[str, Any]:
    return {"amount": 25_000, "category_id": shop.category("Carburant"), **extra}


def test_record_is_idempotent_on_client_id(shop: ExpenseShop) -> None:
    body = fuel(shop, id=str(ExpenseId.new()), tags=["Groupe"])
    captured = (T0 - timedelta(minutes=2)).astimezone().isoformat()
    first = shop.call("POST", "/expenses", shop.accountant, json=body,
                      headers={"X-Captured-At": captured})  # fmt: skip
    assert first.status_code == 201, first.text
    created = first.json()
    assert created["number"] == "D-000001"
    assert created["status"] == "valid"
    assert created["tags"][0]["name"] == "Groupe"
    assert created["editable"]
    assert datetime.fromisoformat(created["captured_at"]) == T0 - timedelta(minutes=2)
    replay = shop.call("POST", "/expenses", shop.accountant, json={**body, "amount": 1})
    assert replay.status_code == 200
    assert (replay.json()["id"], replay.json()["amount"]) == (created["id"], 25_000)
    naive = shop.call("POST", "/expenses", shop.accountant, json=fuel(shop),
                      headers={"X-Captured-At": "2026-11-11T08:00:00"})  # fmt: skip
    assert naive.status_code == 400
    assert shop.call("POST", "/expenses", shop.accountant, json=fuel(shop)).json()["number"] == (
        "D-000002"
    )


def test_validation_errors(shop: ExpenseShop) -> None:
    other = shop.call("POST", "/expenses", shop.accountant,
                      json={"amount": 10, "category_id": shop.category("Autre")})  # fmt: skip
    assert (other.status_code, other.json()["error"]["code"]) == (400, "DESCRIPTION_REQUIRED")
    zero = shop.call("POST", "/expenses", shop.accountant, json=fuel(shop, amount=0))
    assert (zero.status_code, zero.json()["error"]["code"]) == (400, "INVALID_AMOUNT")
    bad_id = shop.call("POST", "/expenses", shop.accountant, json=fuel(shop, location_id="x"))
    assert bad_id.status_code == 400
    old = shop.call("POST", "/expenses", shop.accountant, json=fuel(shop, spent_on="2026-11-02"))
    assert (old.status_code, old.json()["error"]["code"]) == (422, "DATE_OUT_OF_RANGE")


def test_seller_is_refused_and_other_shop_is_not_found(shop: ExpenseShop) -> None:
    created = shop.call("POST", "/expenses", shop.owner, json=fuel(shop)).json()
    for method, suffix in (
        ("GET", "/expenses"),
        ("POST", "/expenses"),
        ("GET", f"/expenses/{created['id']}"),
        ("GET", "/expense-categories"),
        ("GET", "/tags"),
        ("POST", "/tags/merge"),
    ):
        json: dict[str, object] | None = {} if method == "POST" else None
        response = shop.call(method, suffix, shop.seller, json=json)
        assert response.status_code in (400, 403), (suffix, response.text)
    denied = shop.call("GET", "/expenses", shop.seller)
    assert (denied.status_code, denied.json()["error"]["code"]) == (403, "FORBIDDEN")
    other = shop.api.open_motos(shop.api.admin(), "690000009")
    stranger = shop.api.login("690000009", other["temporary_pin"])
    path = f"/shops/{other['shop']['shop_id']}/expenses/{created['id']}"
    assert shop.api.call("GET", path, stranger).status_code == 404
    unknown = shop.call("GET", f"/expenses/{ExpenseId.new()}", shop.owner)
    assert unknown.status_code == 404


def test_correct_cancel_and_window(shop: ExpenseShop) -> None:
    created = shop.call("POST", "/expenses", shop.accountant, json=fuel(shop)).json()
    path = f"/expenses/{created['id']}"
    shop.clock.move_to(datetime(2026, 11, 11, 22, 59, 59, tzinfo=UTC))  # 23:59:59 à Douala
    shop.relogin()
    patched = shop.call("PATCH", path, shop.accountant, json={"version": 1, "amount": 26_000})
    assert (patched.status_code, patched.json()["version"]) == (200, 2), patched.text
    stale = shop.call("PATCH", path, shop.accountant, json={"version": 1, "amount": 1})
    assert stale.json()["error"]["code"] == "VERSION_CONFLICT"
    cleared = shop.call("PATCH", path, shop.accountant, json={"version": 2, "amount": None})
    assert cleared.status_code == 400
    shop.clock.move_to(datetime(2026, 11, 11, 23, 0, tzinfo=UTC))  # minuit à Douala
    shop.relogin()
    late = shop.call("PATCH", path, shop.accountant, json={"version": 2, "tags": ["Fête"]})
    assert (late.status_code, late.json()["error"]["code"]) == (422, "CORRECTION_WINDOW_CLOSED")
    owner = shop.call("PATCH", path, shop.owner, json={"version": 2, "description": None,
                                                       "tags": ["Fête"]})  # fmt: skip
    assert owner.status_code == 200
    assert owner.json()["tags"][0]["name"] == "Fête"
    no_reason = shop.call("POST", f"{path}/cancel", shop.owner, json={"reason": " "})
    assert (no_reason.status_code, no_reason.json()["error"]["code"]) == (400, "REASON_REQUIRED")
    missing = shop.call("POST", f"{path}/cancel", shop.owner, json={})
    assert missing.status_code == 400
    cancelled = shop.call("POST", f"{path}/cancel", shop.owner, json={"reason": "Erreur"})
    body = cancelled.json()
    assert body["status"] == "cancelled"
    assert body["cancellation"]["reason"] == "Erreur"
    twice = shop.call("POST", f"{path}/cancel", shop.owner, json={"reason": "Encore"})
    assert twice.json()["error"]["code"] == "INVALID_STATE_TRANSITION"
    draft = shop.call("GET", f"{path}/repeat", shop.accountant).json()
    assert (draft["amount"], draft["spent_on"]) == (26_000, "2026-11-12")


def test_list_totals_and_filters(shop: ExpenseShop) -> None:
    meal = shop.category("Repas")
    for body in (fuel(shop, tags=["Groupe"]), {"amount": 10_000, "category_id": meal}):
        assert shop.call("POST", "/expenses", shop.accountant, json=body).status_code == 201
    void = shop.call("POST", "/expenses", shop.accountant, json=fuel(shop, amount=7)).json()
    shop.call("POST", f"/expenses/{void['id']}/cancel", shop.accountant, json={"reason": "x"})
    listing = shop.call("GET", "/expenses", shop.accountant).json()
    assert len(listing["items"]) == 3
    assert listing["first_day"] == listing["last_day"]
    assert listing["totals"]["amount"] == 35_000
    assert [t["amount"] for t in listing["totals"]["by_category"]] == [25_000, 10_000]
    query = {"category_id": meal, "limit": 1}
    filtered = shop.call("GET", "/expenses", shop.owner, params=query).json()
    assert filtered["totals"]["amount"] == 10_000
    assert filtered["next_cursor"] is None
    tag_id = shop.call("GET", "/tags", shop.accountant, params={"search": "gro"}).json()[0]["id"]
    by_tag = shop.call("GET", "/expenses", shop.owner, params={"tag_id": tag_id}).json()
    assert by_tag["totals"]["amount"] == 25_000
    page = shop.call("GET", "/expenses", shop.owner, params={"limit": 2}).json()
    rest = shop.call("GET", "/expenses", shop.owner,
                     params={"limit": 2, "cursor": page["next_cursor"]}).json()  # fmt: skip
    assert len(page["items"]) + len(rest["items"]) == 3
    inverted = shop.call("GET", "/expenses", shop.owner,
                         params={"from": "2026-11-11", "to": "2026-11-01"})  # fmt: skip
    assert inverted.status_code == 400


def test_categories_and_tag_merge(shop: ExpenseShop) -> None:
    created = shop.call("POST", "/expense-categories", shop.owner, json={"name": "Eau"})
    assert created.status_code == 201
    category = created.json()
    replay = shop.call("POST", "/expense-categories", shop.owner,
                       json={"id": category["id"], "name": "Autre nom"})  # fmt: skip
    assert replay.status_code == 200
    assert replay.json()["name"] == "Eau"
    assert shop.call("POST", "/expense-categories", shop.accountant,
                     json={"name": "X"}).status_code == 403  # fmt: skip
    rent = next(c for c in shop.call("GET", "/expense-categories", shop.owner).json()
                if c["name"] == "Loyer")  # fmt: skip
    locked = shop.call("PATCH", f"/expense-categories/{rent['id']}", shop.owner,
                       json={"version": rent["version"], "active": False})  # fmt: skip
    assert (locked.status_code, locked.json()["error"]["code"]) == (422, "BASE_CATEGORY_LOCKED")
    off = shop.call("PATCH", f"/expense-categories/{category['id']}", shop.owner,
                    json={"version": 1, "active": False})  # fmt: skip
    assert off.json()["active"] is False
    for name in ("groupe", "Groupe électrogène"):
        shop.call("POST", "/expenses", shop.accountant, json=fuel(shop, tags=[name]))
    tags = {t["name"]: t["id"] for t in shop.call("GET", "/tags", shop.owner).json()}
    merge = {"source_id": tags["groupe"], "target_id": tags["Groupe électrogène"]}
    assert shop.call("POST", "/tags/merge", shop.accountant, json=merge).status_code == 403
    merged = shop.call("POST", "/tags/merge", shop.owner, json=merge)
    assert merged.status_code == 200
    assert merged.json()["retagged_expenses"] == 1
    assert [t["name"] for t in shop.call("GET", "/tags", shop.owner).json()] == [
        "Groupe électrogène"
    ]
