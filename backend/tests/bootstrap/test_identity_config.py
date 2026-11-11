"""Configuration de l'identité (T08) : secret JWT fail-fast, durées, choix de persistance."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.bootstrap.config import (
    ConfigurationError,
    Environment,
    Settings,
    load_settings,
)
from app.bootstrap.container import build_app
from app.bootstrap.identity import build_identity, session_policy_from
from app.infrastructure.persistence.memory.clock import FixedClock
from app.infrastructure.persistence.sqlalchemy.platform_uow import SqlIdentityUnitOfWorkFactory
from tests.application.identity.support import T0

URL = SecretStr("postgresql+psycopg://u:p@127.0.0.1:5432/boutique")


def test_missing_jwt_secret_stops_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.delenv("JWT_SECRET")
    with pytest.raises(ConfigurationError, match="JWT_SECRET"):
        load_settings(env_file=None)
    with pytest.raises(ConfigurationError, match="JWT_SECRET"):
        build_app(env_file=None)


def test_short_jwt_secret_stops_startup_without_echoing_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("JWT_SECRET", "trop-court-0123456789")
    with pytest.raises(ConfigurationError, match="32 octets") as caught:
        load_settings(env_file=None)
    assert "trop-court" not in str(caught.value)


@pytest.mark.parametrize(
    ("name", "value"),
    [("ACCESS_TOKEN_TTL_MINUTES", "0"), ("REFRESH_TOKEN_TTL_DAYS", "400"),
     ("ADMIN_SESSION_TTL_HOURS", "25")],
)  # fmt: skip
def test_durations_are_bounded(monkeypatch: pytest.MonkeyPatch, name: str, value: str) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigurationError, match=name):
        load_settings(env_file=None)


def test_durations_become_the_session_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("ACCESS_TOKEN_TTL_MINUTES", "10")
    monkeypatch.setenv("REFRESH_TOKEN_TTL_DAYS", "7")
    monkeypatch.setenv("ADMIN_SESSION_TTL_HOURS", "4")
    policy = session_policy_from(load_settings(env_file=None))
    assert (policy.access_ttl, policy.refresh_ttl, policy.admin_session_ttl) == (
        timedelta(minutes=10),
        timedelta(days=7),
        timedelta(hours=4),
    )
    with pytest.raises(ValueError, match="positive"):
        type(policy)(access_ttl=timedelta(0))


def test_identity_runs_on_postgres_in_prod_without_connecting() -> None:
    """T10 : l'adaptateur SQL existe, le garde-fou « refus en prod » a disparu."""
    settings = Settings(ENVIRONMENT=Environment.PROD, DATABASE_URL=URL, _env_file=None)
    module = build_identity(settings)
    assert isinstance(module.uow_factory, SqlIdentityUnitOfWorkFactory)
    assert module.auth.throttle is not None  # limitation de débit active hors tests


def test_rate_limit_is_off_in_test_unless_enabled() -> None:
    assert (
        build_identity(Settings(ENVIRONMENT=Environment.TEST, _env_file=None)).auth.throttle is None
    )
    enabled = Settings(ENVIRONMENT=Environment.TEST, AUTH_RATE_LIMIT_ENABLED=True, _env_file=None)
    throttle = build_identity(enabled).auth.throttle
    assert throttle is not None
    rules = throttle.rules
    assert (rules.login_ip.limit, rules.login_phone.limit, rules.refresh_ip.limit) == (10, 5, 30)
    assert (rules.change_pin_ip.limit, rules.login_phone.window) == (10, timedelta(minutes=15))
    module = build_identity(enabled)
    with pytest.raises(ValueError, match="horloge"):
        build_identity(enabled, core=module.core, clock=FixedClock(T0))


def test_assembled_app_exposes_the_auth_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    with TestClient(build_app(env_file=None), base_url="https://testserver") as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": "699999999", "pin": "482915", "device_label": "PC"},
            headers={"X-Device-Id": "019a7d1e-5c4b-7a00-8000-000000000001"},
        )
    assert (response.status_code, response.json()["error"]["code"]) == (401, "UNAUTHENTICATED")
