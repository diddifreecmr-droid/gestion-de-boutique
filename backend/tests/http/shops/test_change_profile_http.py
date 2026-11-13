"""T27 — profil Prêt-à-porter servi (PRF-03) et `POST /platform/shops/{id}/profile` (PRF-06 à 08,
M3-07, ERR3-01)."""

from typing import Any

from tests.http.shops.conftest import Api, Session

OWNER = "690000001"


def menu(profile: dict[str, Any]) -> list[Any]:
    return [
        (e["label"], [c["label"] for c in e["children"]]) if e["children"] else e["label"]
        for e in profile["menu"]
    ]


def open_apparel(api: Api, admin: Session) -> dict[str, Any]:
    body = {
        "profile_code": "apparel",
        "name": "Mode Douala",
        "city": "Douala",
        "phone": "233000000",
        "owner": {"name": "Awa", "phone": OWNER},
    }
    response = api.call("POST", "/platform/shops", admin, json=body)
    assert response.status_code == 201, response.text
    opened: dict[str, Any] = response.json()
    return opened


def staff(api: Api, owner: Session, shop: str, phone: str, role: str) -> Session:
    body: dict[str, Any] = {"name": "Paul", "phone": phone, "role": role}
    if role == "seller":
        places = api.call("GET", f"/shops/{shop}/locations", owner).json()["items"]
        body["default_location_id"] = places[0]["id"]
    added = api.call("POST", f"/shops/{shop}/members", owner, json=body)
    assert added.status_code == 201, added.text
    return api.login(phone, added.json()["temporary_pin"])


def test_prf03_apparel_profile_menus_and_labels(api: Api) -> None:
    opened = open_apparel(api, api.admin())
    shop = opened["shop"]["shop_id"]
    owner = api.login(OWNER, opened["temporary_pin"])
    profile = api.call("GET", f"/shops/{shop}/profile", owner).json()
    assert profile["receipt"]["print_profile"] == "thermal-58"
    assert [r["label"] for r in profile["roles"]] == ["Propriétaire", "Employé", "Comptable"]
    assert menu(profile) == [
        "Accueil", "Ventes", "Stock", "Créances",
        ("Plus", ["Achats", "Dépenses", "Clients", "Journal", "Import", "Réglages"]),
    ]  # fmt: skip
    seller = api.call(
        "GET", f"/shops/{shop}/profile", staff(api, owner, shop, "677000002", "seller")
    )
    assert seller.json()["role_label"] == "Employé"
    assert menu(seller.json()) == ["Accueil", "Nouvelle vente", "Mes ventes", "Créances", "Stock"]
    accountant = staff(api, owner, shop, "677000003", "accountant")
    found = api.call("GET", f"/shops/{shop}/profile", accountant).json()
    assert menu(found) == ["Accueil", "Achats", "Stock", "Dépenses", "Inventaire"]
    driver = {"name": "Ali", "phone": "677000004", "role": "driver"}
    refused = api.call("POST", f"/shops/{shop}/members", owner, json=driver)
    assert refused.json()["error"]["code"] == "ROLE_NOT_IN_PROFILE"


def test_prf06_change_an_empty_shop_type(api: Api) -> None:
    admin = api.admin()
    opened = api.open_motos(admin)
    shop = opened["shop"]["shop_id"]
    path = f"/platform/shops/{shop}/profile"
    changed = api.call("POST", path, admin, json={"profile_code": "apparel"})
    assert changed.status_code == 200, changed.text
    assert changed.json()["profile_code"] == "apparel"
    assert "transport" not in changed.json()["enabled_modules"]
    owner = api.login(OWNER, opened["temporary_pin"])
    places = api.call("GET", f"/shops/{shop}/locations", owner).json()["items"]
    assert {p["name"]: p["active"] for p in places} == {
        "Garoua-Boulaï": False, "Ngaoundéré": False, "Garoua": False, "Boutique": True,
    }  # fmt: skip
    settings = api.call("GET", f"/shops/{shop}/settings", owner).json()
    assert settings["print_profile"] == "thermal-58"
    journal = api.call("GET", f"/shops/{shop}/audit", owner).json()["items"]
    assert any(e["summary"].startswith("Type de boutique") and e["sensitive"] for e in journal)


def test_prf07_prf08_refusals(api: Api) -> None:
    admin = api.admin()
    opened = api.open_motos(admin)
    shop = opened["shop"]["shop_id"]
    path = f"/platform/shops/{shop}/profile"
    owner = api.login(OWNER, opened["temporary_pin"])
    assert api.call("POST", path, owner, json={"profile_code": "apparel"}).status_code == 403
    unknown = api.call("POST", path, admin, json={"profile_code": "epicerie"})
    assert (unknown.status_code, unknown.json()["error"]["code"]) == (400, "UNKNOWN_PROFILE")
    assert api.call("POST", path, admin, json={}).status_code == 400
    nowhere = "/platform/shops/01890a5d-ac96-774b-bcce-b302099a8099/profile"
    assert api.call("POST", nowhere, admin, json={"profile_code": "apparel"}).status_code == 404
    staff(api, owner, shop, "677000004", "driver")
    blocked = api.call("POST", path, admin, json={"profile_code": "textile"})
    assert blocked.status_code == 422
    error = blocked.json()["error"]
    assert (error["code"], error["details"]["blocking"]) == (
        "PROFILE_CHANGE_BLOCKED",
        {"members": 1},
    )
    assert api.call("GET", f"/platform/shops/{shop}", admin).json()["profile_code"] == "motos"
