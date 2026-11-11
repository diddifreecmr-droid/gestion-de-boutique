"""Routes du catalogue : non-fuite des coûts (SEC-N01/N02), droits (M04 à M07), isolation
(SEC-I05), idempotence par `id` client, verrou optimiste (ERR-VER-01), doublon (ERR-DUP-06)."""

from typing import Any

from app.domain.catalog.ids import ArticleId
from tests.http.shops.conftest import Api, Session

OWNER_PHONE = "690000001"
STAFF = {"seller": "677000002", "accountant": "677000003", "driver": "677000004"}
COST_WORDS = ("cost", "wac", "margin", "value")
HJ = {"fields": {"brand": "Haojue", "model": "HJ125-8", "engine_cc": 125}}


class Shop:
    def __init__(self, api: Api) -> None:
        self.api = api
        opened = api.open_motos(api.admin())
        self.id = opened["shop"]["shop_id"]
        self.owner = api.login(OWNER_PHONE, opened["temporary_pin"])
        locations = self.call("GET", "/locations", self.owner).json()["items"]
        garoua = next(loc["id"] for loc in locations if loc["name"] == "Garoua")
        self.staff: dict[str, Session] = {}
        for role, phone in STAFF.items():
            body = {"name": role, "phone": phone, "role": role}
            if role == "seller":
                body["default_location_id"] = garoua
            added = self.call("POST", "/members", self.owner, json=body)
            assert added.status_code == 201, added.text
            self.staff[role] = api.login(phone, added.json()["temporary_pin"])

    def call(self, method: str, suffix: str, who: Session, **kwargs: Any) -> Any:
        return self.api.call(method, f"/shops/{self.id}{suffix}", who, **kwargs)


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for item in value for k in _keys(item)}
    return set()


def test_create_read_and_role_visibility(api: Api) -> None:
    shop = Shop(api)
    created = shop.call("POST", "/articles", shop.owner, json={**HJ, "base_price": 780_000})
    assert created.status_code == 201, created.text
    article = created.json()
    assert (article["display_name"], article["base_price"]) == ("Haojue HJ125-8", 780_000)
    assert article["last_cost"] is None
    assert len(article["price_history"]) == 1
    path = f"/articles/{article['id']}"
    seller = shop.call("GET", path, shop.staff["seller"]).json()
    assert seller["base_price"] == 780_000
    assert "min_price" in seller
    listed = shop.call("GET", "/articles?q=hj", shop.staff["seller"]).json()
    for body in (seller, listed):  # SEC-N01 : aucune clé de coût, même vide
        assert not [k for k in _keys(body) if any(word in k for word in COST_WORDS)]
    assert "price_history" not in seller
    accountant = shop.call("GET", path, shop.staff["accountant"]).json()
    assert "last_cost" in accountant
    assert "base_price" not in accountant
    assert shop.call("GET", path, shop.staff["driver"]).status_code == 403
    assert shop.call("GET", "/articles", shop.staff["driver"]).status_code == 403
    assert [a["display_name"] for a in listed["items"]] == ["Haojue HJ125-8"]
    assert listed["next_cursor"] is None


def test_accountant_writes_without_prices(api: Api) -> None:
    shop = Shop(api)
    accountant = shop.staff["accountant"]
    priced = shop.call("POST", "/articles", accountant, json={**HJ, "base_price": 1})
    assert priced.status_code == 403  # CAT-03 [Q-14]
    created = shop.call("POST", "/articles", accountant, json=HJ)
    assert created.status_code == 201
    assert "base_price" not in created.json()
    path = f"/articles/{created.json()['id']}"
    assert shop.call("PUT", f"{path}/prices", accountant, json={"version": 1}).status_code == 403
    assert shop.call("POST", f"{path}/archive", accountant).status_code == 403
    assert shop.call("POST", "/articles", shop.staff["seller"], json=HJ).status_code == 403
    variant = {"fields": {"brand": "haojue", "model": "hj125 8"}}
    duplicate = shop.call("POST", "/articles", shop.owner, json=variant)
    assert duplicate.status_code == 409  # ERR-DUP-06
    assert duplicate.json()["error"]["details"]["existing_id"] == created.json()["id"]


def test_patch_prices_archive_and_conflicts(api: Api) -> None:
    shop = Shop(api)
    article = shop.call("POST", "/articles", shop.owner, json=HJ).json()
    path = f"/articles/{article['id']}"
    patch = {"version": 1, "fields": {"model": "HJ125-8A"}, "alert_threshold": "4"}
    first = shop.call("PATCH", path, shop.owner, json=patch)
    stale = shop.call("PATCH", path, shop.owner, json=patch)
    assert first.status_code == 200
    assert first.json()["effective_alert_threshold"] == "4"
    assert stale.json()["error"]["code"] == "VERSION_CONFLICT"  # ERR-VER-01

    def put(**body: int) -> Any:
        return shop.call("PUT", f"{path}/prices", shop.owner, json=body)

    priced = put(version=2, base_price=800_000)
    assert priced.json()["base_price"] == 800_000
    minimum = put(version=3, base_price=800_000, min_price=1)
    assert minimum.json()["error"]["code"] == "MIN_PRICE_DISABLED"
    assert put(version=3, base_price=-1).status_code == 400
    archived = shop.call("POST", f"{path}/archive", shop.owner)
    assert archived.json()["status"] == "archived"
    assert shop.call("GET", "/articles", shop.owner).json()["items"] == []
    assert len(shop.call("GET", "/articles?status=all", shop.owner).json()["items"]) == 1
    again = shop.call("POST", f"{path}/archive", shop.owner)
    assert again.json()["error"]["code"] == "INVALID_STATE_TRANSITION"
    assert shop.call("POST", f"{path}/reactivate", shop.owner).json()["status"] == "active"
    sort = shop.call("GET", "/articles?sort=best_selling", shop.owner)
    assert sort.json()["error"]["code"] == "SORT_UNAVAILABLE"
    assert shop.call("GET", "/articles?cursor=%25%25", shop.owner).status_code == 400


def test_idempotent_creation_and_cross_shop_404(api: Api) -> None:
    shop = Shop(api)
    wanted = str(ArticleId.new())
    body = {**HJ, "id": wanted}
    assert shop.call("POST", "/articles", shop.owner, json=body).status_code == 201
    replay = shop.call("POST", "/articles", shop.owner, json=body)
    assert (replay.status_code, replay.json()["id"]) == (200, wanted)
    other = api.call("POST", "/platform/shops", api.admin(), json={
        "profile_code": "motos", "name": "Motos Ngaoundéré", "city": "Ngaoundéré",
        "phone": "222000001", "owner": {"name": "Moussa", "phone": OWNER_PHONE},
    })  # fmt: skip
    assert other.status_code == 201
    assert other.json()["temporary_pin"] is None
    foreign = f"/shops/{other.json()['shop']['shop_id']}/articles/{wanted}"
    assert api.call("GET", foreign, shop.owner).status_code == 404  # SEC-I05
    patched = api.call("PATCH", foreign, shop.owner, json={"version": 1, "notes": "x"})
    assert patched.status_code == 404
    assert shop.call("GET", f"/articles/{wanted}", shop.owner).json()["version"] == 1
    bad = shop.call("POST", "/articles", shop.owner, json={"fields": {"brand": "X"}})
    assert bad.status_code == 400
    photo = shop.call("POST", "/articles", shop.owner, json={**HJ, "photo_id": "nope"})
    assert photo.status_code == 400
