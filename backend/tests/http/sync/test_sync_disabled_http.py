"""Droit `offline_capture` inactif (V1, D8, TR-26) : `POST /sync` et l'instantané répondent
403 `FEATURE_DISABLED` pour tous les rôles, sans rien écrire (OFF-01, OFF-02) ; le profil
expose le droit au frontend ; une surcharge de l'administrateur l'ouvre pour **une** boutique
sans redéploiement, et le retrait la referme (ERR-FEA-04)."""

from tests.http.sync.conftest import Desk


def test_v1_shop_refuses_sync_and_snapshot_for_every_role(desk: Desk) -> None:
    who = [desk.shop.owner, *desk.shop.staff.values()]
    for session in who:
        refused = desk.sync(session, desk.op(session, 1, desk.sale_payload()))
        assert refused.status_code == 403, refused.text
        assert refused.json()["error"]["code"] == "FEATURE_DISABLED"
        assert refused.json()["error"]["details"] == {"entitlement": "offline_capture"}
        snapshot = desk.call("GET", "/offline-snapshot", session)
        assert snapshot.json()["error"]["code"] == "FEATURE_DISABLED"
        profile = desk.ok("GET", "/profile", session)
        assert profile["entitlements"] == {"offline_capture": False}
    assert desk.ok("GET", "/sales?from=2026-01-01", desk.shop.owner)["items"] == []


def test_admin_override_opens_one_shop_only_then_closes_it(desk: Desk) -> None:
    other = desk.api.open_motos(desk.api.admin(), owner_phone="690000099")
    other_owner = desk.api.login("690000099", other["temporary_pin"])
    other_path = f"/shops/{other['shop']['shop_id']}/sync"
    desk.enable()
    seller = desk.staff("seller")
    assert desk.ok("GET", "/profile", seller)["entitlements"] == {"offline_capture": True}
    assert desk.sync(seller).json() == {"results": []}
    body = {"device_id": str(other_owner.device), "operations": []}
    closed = desk.api.call("POST", other_path, other_owner, json=body)
    assert closed.json()["error"]["code"] == "FEATURE_DISABLED"
    desk.enable(None)  # retrait de la surcharge : l'offre gratuite décide de nouveau
    assert desk.sync(seller).status_code == 403
    desk.enable(False)
    assert desk.call("GET", "/offline-snapshot", seller).status_code == 403
