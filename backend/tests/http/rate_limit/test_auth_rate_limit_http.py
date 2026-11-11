"""429 `RATE_LIMITED` sur `/auth/*` (specs § 8.1, recette SEC-L09 / Q-41, T10b).

Seuils par défaut : connexion 10/min par IP et 5/15 min par numéro, refresh 30/min,
change-pin 10/min par IP ; logout non limité.
"""

from datetime import timedelta

from tests.http.rate_limit.support import build_api

IP = "203.0.113.7"


def numbers(count: int) -> list[str]:
    return [f"6770011{index:02d}" for index in range(count)]


def test_login_beyond_ten_per_ip_is_429_with_body_and_header() -> None:
    api = build_api()
    assert [api.login(IP, phone).status_code for phone in numbers(10)] == [401] * 10
    refused = api.login(IP, "699999999")
    assert refused.status_code == 429
    assert refused.json() == {
        "error": {
            "code": "RATE_LIMITED",
            "message": "Trop de tentatives : réessayez plus tard",
            "details": {"retry_after": 60},
        }
    }
    assert refused.headers["retry-after"] == "60"
    assert api.login("198.51.100.1", "699999999").status_code == 401  # autre IP : libre
    api.clock.advance(timedelta(seconds=60))
    assert api.login(IP, "699999999").status_code == 401


def test_one_number_is_limited_across_ips_and_spellings() -> None:
    api = build_api()
    spellings = ["677001122", "677 00 11 22", "+237677001122", "00237677001122", "237677001122"]
    for index, phone in enumerate(spellings):
        assert api.login(f"198.51.100.{index}", phone).status_code == 401
    refused = api.login("198.51.100.99", "+237 677-00-11-22")
    assert refused.status_code == 429
    assert refused.json()["error"]["details"] == {"retry_after": 900}
    assert refused.headers["retry-after"] == "900"
    assert api.login("198.51.100.99", "699999999").status_code == 401  # autre numéro : libre


def test_invalid_inputs_share_one_counter_per_ip() -> None:
    api = build_api()
    invalid = [f"pas-un-numero-{index}" for index in range(5)]
    assert [api.login(IP, phone).status_code for phone in invalid] == [401] * 5
    assert api.login(IP, "encore-autre-chose").status_code == 429
    assert api.login(IP, "677001122").status_code == 401  # numéro valide : son propre compteur
    assert api.login("198.51.100.1", "pas-un-numero-0").status_code == 401  # autre IP


def test_refresh_and_change_pin_have_their_own_ip_threshold() -> None:
    api = build_api()
    assert {api.post(IP, "/auth/refresh").status_code for _ in range(30)} == {401}
    assert api.post(IP, "/auth/refresh").status_code == 429
    # Limité avant l'authentification : un jeton deviné est freiné lui aussi.
    assert {api.post(IP, "/auth/change-pin").status_code for _ in range(10)} == {401}
    change_pin = api.post(IP, "/auth/change-pin")
    assert (change_pin.status_code, change_pin.headers["retry-after"]) == (429, "60")
    assert api.login(IP).status_code == 401  # compteur de connexion intact


def test_logout_is_never_limited() -> None:
    api = build_api()
    assert {api.post(IP, "/auth/logout").status_code for _ in range(100)} == {401}


def test_forwarded_for_is_ignored_without_trusted_proxy() -> None:
    api = build_api()
    for index, phone in enumerate(numbers(10)):
        assert api.login("10.0.0.5", phone, forwarded_for=f"203.0.113.{index}").status_code == 401
    assert api.login("10.0.0.5", "699999999", forwarded_for="203.0.113.200").status_code == 429


def test_forwarded_for_is_used_behind_a_trusted_proxy() -> None:
    api = build_api(trusted_proxies="10.0.0.0/8")
    # Chaque client réel a son compteur, bien que tous passent par le même proxy.
    for index, phone in enumerate(numbers(10)):
        assert api.login("10.0.0.5", phone, forwarded_for=f"203.0.113.{index}").status_code == 401
    for phone in numbers(9):
        assert api.login("10.0.0.5", phone, forwarded_for="203.0.113.0").status_code == 401
    # Le client forge la partie gauche : seule l'adresse ajoutée par le proxy compte.
    spoofed = api.login("10.0.0.5", "699999999", forwarded_for="1.2.3.4, 203.0.113.0")
    assert spoofed.status_code == 429
