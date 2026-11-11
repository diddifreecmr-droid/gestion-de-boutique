"""Refresh, logout, `/me`, change-pin et `current_actor` de bout en bout (AUTH-02, SEC-R)."""

from datetime import timedelta

from app.application.identity.use_cases.member_access import MemberAccess
from app.application.identity.use_cases.revoke_user_devices import RevokeUserDevices
from app.application.security.actor import Actor
from app.application.security.policy import Policy
from app.application.security.roles import Role
from app.domain.shared.ids import DeviceId, ShopId, UserId
from tests.application.identity.support import PIN
from tests.http.auth.support import PREFIX, SHOP, Api


def logged_in(api: Api, device: DeviceId, *, must_change: bool = False) -> tuple[str, str]:
    api.register(must_change=must_change)
    response = api.login(device)
    return response.json()["access_token"], response.cookies["refresh_token"]


def test_refresh_rotates_and_reuse_revokes(api: Api) -> None:
    device = DeviceId.new()
    _, first = logged_in(api, device)
    rotated = api.with_cookie("/auth/refresh", device, first)
    assert rotated.status_code == 200
    second = rotated.cookies["refresh_token"]
    assert second != first
    assert "HttpOnly" in rotated.headers["set-cookie"]
    reused = api.with_cookie("/auth/refresh", device, first)
    assert (reused.status_code, reused.json()["error"]["code"]) == (401, "SESSION_REVOKED")
    after = api.with_cookie("/auth/refresh", device, second)
    assert after.json()["error"]["code"] == "SESSION_REVOKED"


def test_refresh_without_cookie_is_unauthenticated(api: Api) -> None:
    api.client.cookies.clear()
    response = api.client.post(
        f"{PREFIX}/auth/refresh", headers={"X-Device-Id": str(DeviceId.new())}
    )
    assert (response.status_code, response.json()["error"]["code"]) == (401, "UNAUTHENTICATED")


def test_logout_clears_the_cookie_and_ends_the_session(api: Api) -> None:
    device = DeviceId.new()
    access, refresh = logged_in(api, device)
    response = api.with_cookie("/auth/logout", device, refresh)
    assert response.status_code == 204
    cookie = response.headers["set-cookie"]
    assert "Max-Age=0" in cookie
    assert "Path=/api/v1/auth" in cookie
    assert api.get("/me", device, access).json()["error"]["code"] == "SESSION_REVOKED"
    assert api.with_cookie("/auth/logout", device, "pas-un-jeton").status_code == 401


def test_first_login_flow_requires_a_pin_change(api: Api) -> None:
    device = DeviceId.new()
    access, _ = logged_in(api, device, must_change=True)
    me = api.get("/me", device, access)
    assert me.status_code == 200
    assert me.json()["must_change_pin"] is True
    assert me.json()["shops"] == [
        {"shop_id": str(SHOP), "shop_name": "Motos Garoua", "role": "seller"}
    ]
    blocked = api.get(f"/shops/{SHOP}/probe", device, access)
    assert (blocked.status_code, blocked.json()["error"]["code"]) == (403, "PIN_CHANGE_REQUIRED")
    headers = {"X-Device-Id": str(device), "Authorization": f"Bearer {access}"}
    simple = {"current_pin": PIN, "new_pin": "123456", "new_pin_confirmation": "123456"}
    refused = api.client.post(f"{PREFIX}/auth/change-pin", json=simple, headers=headers)
    assert (refused.status_code, refused.json()["error"]["code"]) == (422, "PIN_TOO_SIMPLE")
    good = {"current_pin": PIN, "new_pin": "730518", "new_pin_confirmation": "730518"}
    changed = api.client.post(f"{PREFIX}/auth/change-pin", json=good, headers=headers)
    assert changed.status_code == 204
    allowed = api.get(f"/shops/{SHOP}/probe", device, access)
    assert (allowed.status_code, allowed.json()) == (200, {"role": "seller"})


def test_current_actor_hides_foreign_shops_and_needs_a_token(api: Api) -> None:
    device = DeviceId.new()
    access, _ = logged_in(api, device)
    foreign = api.get(f"/shops/{ShopId.new()}/probe", device, access)
    assert (foreign.status_code, foreign.json()["error"]["code"]) == (404, "NOT_FOUND")
    anonymous = api.client.get(f"{PREFIX}/shops/{SHOP}/probe", headers={"X-Device-Id": str(device)})
    assert (anonymous.status_code, anonymous.json()["error"]["code"]) == (401, "UNAUTHENTICATED")
    blank = api.client.get(
        f"{PREFIX}/shops/{SHOP}/probe",
        headers={"X-Device-Id": str(device), "Authorization": "Bearer   "},
    )
    assert blank.status_code == 401
    other_device = api.get(f"/shops/{SHOP}/probe", DeviceId.new(), access)
    assert other_device.status_code == 401
    api.clock.advance(timedelta(minutes=15))
    assert api.get(f"/shops/{SHOP}/probe", device, access).status_code == 401


def test_remote_revocation_applies_to_the_current_access_token(api: Api) -> None:
    device = DeviceId.new()
    access, refresh = logged_in(api, device)
    me = api.get("/me", device, access).json()
    owner = Actor.member(
        user_id=UserId.new(), device_id=DeviceId.new(), shop_id=SHOP, role=Role.OWNER
    )
    access_guard = MemberAccess(Policy(clock=api.clock.now), api.module.memberships)
    revoke = RevokeUserDevices(api.module.uow_factory, access_guard, api.clock)
    assert revoke.execute(owner, UserId.parse(me["user_id"])) == 1
    response = api.get(f"/shops/{SHOP}/probe", device, access)
    assert (response.status_code, response.json()["error"]["code"]) == (401, "SESSION_REVOKED")
    assert api.with_cookie("/auth/refresh", device, refresh).status_code == 401
    assert api.login(device).status_code == 200
