"""Routes plateforme et boutique (PLT-01 à 04, M01 à M03, MEM-02, SET-02, LOC-01, SEC-X)."""

from typing import Any

from tests.http.shops.conftest import Api, Session

SELLER = "677000002"


def shop_path(opened: dict[str, Any], suffix: str) -> str:
    return f"/shops/{opened['shop']['shop_id']}{suffix}"


def owner_of(api: Api, opened: dict[str, Any]) -> Session:
    return api.login("690000001", opened["temporary_pin"])


def test_platform_console(api: Api) -> None:
    admin = api.admin()
    opened = api.open_motos(admin)
    assert opened["owner_created"]
    assert len(opened["temporary_pin"]) == 6
    assert opened["shop"]["enabled_modules"][0] == "audit"
    missing = api.call("POST", "/platform/shops", admin, json={"profile_code": "motos"})
    assert missing.status_code == 400
    fields = {f["field"] for f in missing.json()["error"]["details"]["fields"]}
    assert {"body.name", "body.city", "body.phone"} <= fields
    owner = owner_of(api, opened)
    assert api.call("POST", "/platform/shops", owner, json={}).status_code == 403
    assert api.call("GET", "/platform/shops", owner).status_code == 403
    listed = api.call("GET", "/platform/shops", admin).json()
    assert [s["name"] for s in listed] == ["Motos Garoua"]
    shop_id = opened["shop"]["shop_id"]
    patch = {"status": "closed", "entitlements": {"offline_capture": True}}
    patched = api.call("PATCH", f"/platform/shops/{shop_id}", admin, json=patch)
    assert patched.json()["status"] == "closed"
    closed = api.call("GET", shop_path(opened, "/profile"), owner)  # sa seule boutique est fermée
    assert closed.json()["error"]["code"] == "ACCOUNT_DISABLED"
    bad = api.call("PATCH", f"/platform/shops/{shop_id}", admin, json={"modules": ["nope"]})
    assert bad.status_code == 400
    assert api.call("GET", f"/platform/shops/{shop_id}", admin).status_code == 200
    unknown = {**_body(), "profile_code": "epicerie"}
    refused = api.call("POST", "/platform/shops", admin, json=unknown)
    assert refused.json()["error"]["code"] == "UNKNOWN_PROFILE"


def test_profile_settings_and_places(api: Api) -> None:
    opened = api.open_motos(api.admin())
    owner = owner_of(api, opened)
    profile = api.call("GET", shop_path(opened, "/profile"), owner).json()
    assert profile["role_label"] == "Propriétaire"
    assert profile["receipt"]["print_profile"] == "thermal-80"
    assert [entry["code"] for entry in profile["menu"]][-1] == "more"
    settings = api.call("GET", shop_path(opened, "/settings"), owner).json()
    for patch in ({"copies": 0}, {"copies": 4}, {"footer_message": "x" * 201}):
        response = api.call(
            "PATCH", shop_path(opened, "/settings"), owner, json={"version": 1, **patch}
        )
        assert response.status_code == 400, patch
    reception = settings["reception_location_id"]
    ok = api.call("PATCH", shop_path(opened, "/settings"), owner, json={
        "version": 1, "footer_message": "Merci", "reception_location_id": reception,
    })  # fmt: skip
    assert ok.status_code == 200
    assert ok.json()["version"] == 2
    stale = api.call(
        "PATCH", shop_path(opened, "/settings"), owner, json={"version": 1, "copies": 2}
    )
    assert stale.json()["error"]["code"] == "VERSION_CONFLICT"
    created = api.call("POST", shop_path(opened, "/locations"), owner, json={
        "name": "Maroua", "kind": "store", "is_point_of_sale": True,
    })  # fmt: skip
    assert created.status_code == 201
    replay = {
        "id": created.json()["id"],
        "name": "Maroua",
        "kind": "store",
        "is_point_of_sale": True,
    }
    assert api.call("POST", shop_path(opened, "/locations"), owner, json=replay).status_code == 200
    twin = {"name": "maroua", "kind": "store", "is_point_of_sale": True}
    assert api.call("POST", shop_path(opened, "/locations"), owner, json=twin).status_code == 409
    renamed = api.call("PATCH", shop_path(opened, f"/locations/{created.json()['id']}"), owner,
                       json={"version": 1, "name": "Maroua centre"})  # fmt: skip
    assert renamed.json()["name"] == "Maroua centre"
    wave = api.call("POST", shop_path(opened, "/payment-modes"), owner, json={"name": "Wave"})
    assert wave.status_code == 201
    mode = wave.json()["id"]
    off = api.call("PATCH", shop_path(opened, f"/payment-modes/{mode}"), owner,
                   json={"version": 1, "active": False})  # fmt: skip
    assert off.json()["active"] is False
    assert len(api.call("GET", shop_path(opened, "/payment-modes"), owner).json()) == 7


def test_members_and_roles(api: Api) -> None:
    opened = api.open_motos(api.admin())
    owner = owner_of(api, opened)
    locations = api.call("GET", shop_path(opened, "/locations"), owner).json()["items"]
    garoua = next(loc["id"] for loc in locations if loc["name"] == "Garoua")
    depot = next(loc["id"] for loc in locations if loc["name"] == "Ngaoundéré")
    body = {"name": "Paul", "phone": SELLER, "role": "seller", "default_location_id": depot}
    refused = api.call("POST", shop_path(opened, "/members"), owner, json=body)
    assert refused.json()["error"]["code"] == "LOCATION_NOT_POINT_OF_SALE"
    added = api.call(
        "POST", shop_path(opened, "/members"), owner, json={**body, "default_location_id": garoua}
    )
    assert added.status_code == 201
    assert added.headers["Cache-Control"] == "no-store"
    pin = added.json()["temporary_pin"]
    seller = api.login(SELLER, pin)
    for method, path in (("GET", "/members"), ("GET", "/locations"), ("PATCH", "/settings")):
        assert (
            api.call(method, shop_path(opened, path), seller, json={"version": 1}).status_code
            == 403
        )
    assert api.call("GET", shop_path(opened, "/payment-modes"), seller).status_code == 200
    assert api.call("GET", shop_path(opened, "/profile"), seller).json()["role_label"] == "Vendeur"
    uid = added.json()["member"]["user_id"]
    for action in ("revoke-devices", "reset-pin"):
        assert (
            api.call("POST", shop_path(opened, f"/members/{uid}/{action}"), owner).status_code
            == 200
        )
    assert api.call("POST", shop_path(opened, f"/members/{uid}/unlock"), owner).status_code == 422
    members = api.call("GET", shop_path(opened, "/members"), owner).json()
    me = next(m for m in members if m["role"] == "owner")
    last = api.call("PATCH", shop_path(opened, f"/members/{me['user_id']}"), owner,
                    json={"version": me["version"], "active": False})  # fmt: skip
    assert last.json()["error"]["code"] == "LAST_ACTIVE_OWNER"
    target = next(m for m in members if m["role"] == "seller")
    off = api.call("PATCH", shop_path(opened, f"/members/{uid}"), owner,
                   json={"version": target["version"], "role": "accountant",
                         "active": False})  # fmt: skip
    assert off.status_code == 200
    assert off.json()["default_location_id"] is None


def test_admin_access_routes(api: Api) -> None:
    admin = api.admin()
    opened = api.open_motos(admin)
    owner = owner_of(api, opened)
    assert api.call("GET", shop_path(opened, "/profile"), admin).status_code == 404
    assert api.call("GET", shop_path(opened, "/admin-access"), owner).json()["active"] is False
    assert api.call("POST", shop_path(opened, "/admin-access"), owner).status_code == 201
    assert api.call("GET", shop_path(opened, "/profile"), admin).json()["role"] is None
    assert (
        api.call("PATCH", shop_path(opened, "/settings"), admin, json={"version": 1}).status_code
        == 403
    )
    assert api.call("DELETE", shop_path(opened, "/admin-access"), owner).status_code == 204
    assert api.call("DELETE", shop_path(opened, "/admin-access"), owner).status_code == 422
    assert api.call("GET", shop_path(opened, "/profile"), admin).status_code == 404


def test_platform_shop_access(api: Api) -> None:
    admin = api.admin()
    opened = api.open_motos(admin)
    owner = owner_of(api, opened)
    path = f"/platform/shops/{opened['shop']['shop_id']}/access"
    body = api.call("GET", path, admin).json()
    assert body["entitlements"] == [{"code": "offline_capture", "enabled": False, "override": None}]
    assert body["admin_access_until"] is None
    granted = api.call("POST", shop_path(opened, "/admin-access"), owner).json()
    assert api.call("GET", path, admin).json()["admin_access_until"] == granted["expires_at"]
    assert api.call("GET", path, owner).status_code == 403
    unknown = api.call("GET", "/platform/shops/01890a5d-ac96-774b-bcce-b302099a8099/access", admin)
    assert unknown.status_code == 404


def _body() -> dict[str, Any]:
    return {
        "profile_code": "motos",
        "name": "Autre",
        "city": "Garoua",
        "phone": "222000000",
        "owner": {"name": "Moussa", "phone": "690000003"},
    }
