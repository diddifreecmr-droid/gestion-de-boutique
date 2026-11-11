"""Réglages de limitation de débit (T10b) : bornes, proxys de confiance, câblage."""

from ipaddress import ip_network

import pytest

from app.bootstrap.config import ConfigurationError, Environment, Settings, load_settings
from app.bootstrap.identity import build_identity


@pytest.mark.parametrize(
    ("name", "value"),
    [("AUTH_RATE_LIMIT_LOGIN_PER_IP", "0"), ("AUTH_RATE_LIMIT_LOGIN_PER_PHONE", "-1"),
     ("AUTH_RATE_LIMIT_PHONE_WINDOW_MINUTES", "0"), ("AUTH_RATE_LIMIT_REFRESH_PER_IP", "0"),
     ("AUTH_RATE_LIMIT_CHANGE_PIN_PER_IP", "beaucoup"), ("AUTH_RATE_LIMIT_ENABLED", "peut-être"),
     ("AUTH_TRUSTED_PROXIES", "caddy"), ("AUTH_TRUSTED_PROXIES", "10.0.0.1/8")],
)  # fmt: skip
def test_invalid_values_stop_startup(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigurationError, match=name):
        load_settings(env_file=None)


def test_trusted_proxies_are_read_as_a_comma_separated_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("AUTH_TRUSTED_PROXIES", " 172.18.0.0/16 , 127.0.0.1,,::1 ")
    settings = load_settings(env_file=None)
    proxies = settings.AUTH_TRUSTED_PROXIES
    assert proxies == (
        ip_network("172.18.0.0/16"),
        ip_network("127.0.0.1/32"),
        ip_network("::1/128"),
    )
    assert build_identity(settings).auth.trusted_proxies == proxies


def test_no_trusted_proxy_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    assert load_settings(env_file=None).AUTH_TRUSTED_PROXIES == ()


def test_thresholds_become_the_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    for name, value in {
        "AUTH_RATE_LIMIT_ENABLED": "true",
        "AUTH_RATE_LIMIT_LOGIN_PER_IP": "3",
        "AUTH_RATE_LIMIT_LOGIN_PER_PHONE": "2",
        "AUTH_RATE_LIMIT_PHONE_WINDOW_MINUTES": "30",
        "AUTH_RATE_LIMIT_REFRESH_PER_IP": "7",
        "AUTH_RATE_LIMIT_CHANGE_PIN_PER_IP": "4",
    }.items():
        monkeypatch.setenv(name, value)
    throttle = build_identity(load_settings(env_file=None)).auth.throttle
    assert throttle is not None
    rules = throttle.rules
    limits = [r.limit for r in (rules.login_ip, rules.login_phone, rules.refresh_ip,
                                rules.change_pin_ip)]  # fmt: skip
    assert limits == [3, 2, 7, 4]
    assert rules.login_phone.window.total_seconds() == 30 * 60


def test_rate_limit_can_be_disabled_explicitly() -> None:
    settings = Settings(ENVIRONMENT=Environment.TEST, AUTH_RATE_LIMIT_ENABLED=False, _env_file=None)
    assert build_identity(settings).auth.throttle is None
