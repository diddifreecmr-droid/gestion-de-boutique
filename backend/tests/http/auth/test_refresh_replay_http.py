"""`POST /auth/refresh` après une réponse perdue (audit du 2026-11-13, specs § 8.1)."""

from datetime import timedelta

from app.domain.identity.refresh_rotation import REFRESH_REPLAY_GRACE
from app.domain.shared.ids import DeviceId
from tests.http.auth.support import Api
from tests.http.auth.test_session_http import logged_in


def test_lost_refresh_response_is_replayed_with_the_same_cookie(api: Api) -> None:
    device = DeviceId.new()
    _, first = logged_in(api, device)
    lost = api.with_cookie("/auth/refresh", device, first)  # le navigateur ne la reçoit pas
    assert lost.status_code == 200
    api.clock.advance(timedelta(seconds=5))
    replayed = api.with_cookie("/auth/refresh", device, first)
    assert replayed.status_code == 200
    assert replayed.cookies["refresh_token"] == lost.cookies["refresh_token"]
    assert "HttpOnly" in replayed.headers["set-cookie"]
    fresh = replayed.json()["access_token"]
    assert api.get("/me", device, fresh).status_code == 200
    following = api.with_cookie("/auth/refresh", device, replayed.cookies["refresh_token"])
    assert following.status_code == 200


def test_replay_after_the_window_still_ends_the_session(api: Api) -> None:
    device = DeviceId.new()
    _, first = logged_in(api, device)
    second = api.with_cookie("/auth/refresh", device, first).cookies["refresh_token"]
    api.clock.advance(REFRESH_REPLAY_GRACE + timedelta(seconds=1))
    reused = api.with_cookie("/auth/refresh", device, first)
    assert (reused.status_code, reused.json()["error"]["code"]) == (401, "SESSION_REVOKED")
    after = api.with_cookie("/auth/refresh", device, second)
    assert after.json()["error"]["code"] == "SESSION_REVOKED"


def test_replaced_cookie_from_another_device_ends_the_session(api: Api) -> None:
    device = DeviceId.new()
    _, first = logged_in(api, device)
    second = api.with_cookie("/auth/refresh", device, first).cookies["refresh_token"]
    stolen = api.with_cookie("/auth/refresh", DeviceId.new(), first)
    assert (stolen.status_code, stolen.json()["error"]["code"]) == (401, "SESSION_REVOKED")
    assert api.with_cookie("/auth/refresh", device, second).status_code == 401
