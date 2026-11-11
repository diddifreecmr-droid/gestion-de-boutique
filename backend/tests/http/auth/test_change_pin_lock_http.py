"""`POST /auth/change-pin` bloqué : 423 `PIN_CHANGE_LOCKED`, le reste continue (T08 bis)."""

from datetime import timedelta

from app.domain.shared.ids import DeviceId
from tests.application.identity.support import PIN, T0
from tests.http.auth.support import PREFIX, SHOP, Api


def test_change_pin_lock_is_423_and_leaves_the_session_usable(api: Api) -> None:
    api.register()
    device = DeviceId.new()
    access = api.login(device).json()["access_token"]
    headers = {"X-Device-Id": str(device), "Authorization": f"Bearer {access}"}

    def change(current: str) -> int:
        body = {"current_pin": current, "new_pin": "730518", "new_pin_confirmation": "730518"}
        response = api.client.post(f"{PREFIX}/auth/change-pin", json=body, headers=headers)
        return response.status_code

    assert [change("999111") for _ in range(5)] == [422] * 5
    locked = api.client.post(
        f"{PREFIX}/auth/change-pin",
        json={"current_pin": PIN, "new_pin": "730518", "new_pin_confirmation": "730518"},
        headers=headers,
    )
    assert locked.status_code == 423
    assert locked.json()["error"]["code"] == "PIN_CHANGE_LOCKED"
    assert locked.json()["error"]["details"] == {"until": (T0 + timedelta(minutes=15)).isoformat()}
    assert api.get("/me", device, access).status_code == 200
    assert api.get(f"/shops/{SHOP}/probe", device, access).status_code == 200
    assert api.login(DeviceId.new()).status_code == 200
    api.clock.advance(timedelta(minutes=15))
    fresh = api.login(device).json()["access_token"]
    headers["Authorization"] = f"Bearer {fresh}"
    assert change(PIN) == 204


def test_wrong_current_code_is_422_and_the_session_stays_valid(api: Api) -> None:
    api.register()
    device = DeviceId.new()
    access = api.login(device).json()["access_token"]
    headers = {"X-Device-Id": str(device), "Authorization": f"Bearer {access}"}
    body = {"current_pin": "999111", "new_pin": "730518", "new_pin_confirmation": "730518"}
    response = api.client.post(f"{PREFIX}/auth/change-pin", json=body, headers=headers)
    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "CURRENT_PIN_INVALID",
        "message": "Code actuel incorrect",
        "details": {"remaining_attempts": 4},
    }
    assert "www-authenticate" not in response.headers
    assert api.get("/me", device, access).status_code == 200
