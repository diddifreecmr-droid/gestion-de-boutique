"""`POST /auth/login` : cookie (AUTH-01), aucune fuite (SEC-L08), 423 (SEC-L03), en-têtes."""

from datetime import timedelta

from app.domain.shared.ids import DeviceId, UserId
from tests.application.identity.support import T0
from tests.http.auth.support import PREFIX, Api


def test_login_sets_an_httponly_refresh_cookie_and_returns_the_access_token(api: Api) -> None:
    api.register()
    response = api.login(DeviceId.new())
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "token_type", "expires_at", "must_change_pin"}
    assert body["token_type"] == "bearer"
    assert body["must_change_pin"] is False
    cookie = response.headers["set-cookie"]
    for attribute in ("refresh_token=", "HttpOnly", "Secure", "SameSite=lax", "Path=/api/v1/auth"):
        assert attribute in cookie
    assert f"Max-Age={int(timedelta(days=30).total_seconds())}" in cookie
    assert response.headers["cache-control"] == "no-store"
    assert body["access_token"] not in cookie


def test_unknown_number_and_wrong_code_are_indistinguishable(api: Api) -> None:
    api.register()
    wrong = api.login(DeviceId.new(), pin="999111")
    unknown = api.login(DeviceId.new(), phone="699999999")
    malformed = api.login(DeviceId.new(), phone="pas-un-numero")
    for response in (wrong, unknown, malformed):
        assert response.status_code == 401
        assert response.json() == {
            "error": {
                "code": "UNAUTHENTICATED",
                "message": "Numéro ou code incorrect",
                "details": {},
            }
        }
        assert response.headers["www-authenticate"] == "Bearer"
        assert "set-cookie" not in response.headers


def test_fifth_failure_then_423_with_until(api: Api) -> None:
    api.register()
    device = DeviceId.new()
    for _ in range(5):
        assert api.login(device, pin="999111").status_code == 401
    response = api.login(device)
    assert response.status_code == 423
    assert response.json()["error"]["code"] == "ACCOUNT_LOCKED"
    assert response.json()["error"]["details"] == {
        "until": (T0 + timedelta(minutes=15)).isoformat()
    }
    api.clock.advance(timedelta(minutes=15))
    assert api.login(device).status_code == 200


def test_disabled_account_gets_the_cdc_message(api: Api) -> None:
    user = api.register()
    with api.module.uow_factory() as uow:
        stored = uow.users.get(user.id)
        stored.disable(T0, by=UserId.new())
        uow.users.update(stored)
        uow.commit()
    response = api.login(DeviceId.new())
    assert response.status_code == 403
    assert response.json()["error"] == {
        "code": "ACCOUNT_DISABLED",
        "message": "Compte désactivé, contactez le propriétaire",
        "details": {},
    }


def test_device_header_is_mandatory_and_must_be_a_uuid7(api: Api) -> None:
    body = {"phone": "677001122", "pin": "482915", "device_label": "PC"}
    missing = api.client.post(f"{PREFIX}/auth/login", json=body)
    assert missing.status_code == 400
    assert missing.json()["error"]["details"]["fields"][0]["field"] == "header.x-device-id"
    invalid = api.client.post(f"{PREFIX}/auth/login", json=body, headers={"X-Device-Id": "abc"})
    assert (invalid.status_code, invalid.json()["error"]["code"]) == (400, "INVALID_IDENTIFIER")


def test_exactly_one_secret_is_required(api: Api) -> None:
    headers = {"X-Device-Id": str(DeviceId.new())}
    for extra in ({}, {"pin": "482915", "password": "Une phrase longue"}):
        body = {"phone": "677001122", "device_label": "PC", **extra}
        response = api.client.post(f"{PREFIX}/auth/login", json=body, headers=headers)
        assert response.status_code == 400
        assert "482915" not in response.text
