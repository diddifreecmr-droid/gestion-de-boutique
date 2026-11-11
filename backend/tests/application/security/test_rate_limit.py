"""`AuthThrottle` : clé E.164 du numéro, repli des saisies invalides, délai arrondi (T10b)."""

from datetime import timedelta

import pytest

from app.application.security.errors import RateLimited
from app.application.security.rate_limit import (
    AuthRateRules,
    AuthThrottle,
    RateLimitRule,
    phone_key,
)
from app.infrastructure.persistence.memory.clock import FixedClock
from app.infrastructure.rate_limit import InMemoryRateLimiter
from tests.application.identity.support import T0

MINUTE = timedelta(minutes=1)


def rules(login_phone: int = 2) -> AuthRateRules:
    return AuthRateRules(
        login_ip=RateLimitRule("login_ip", 10, MINUTE),
        login_phone=RateLimitRule("login_phone", login_phone, timedelta(minutes=15)),
        refresh_ip=RateLimitRule("refresh_ip", 10, MINUTE),
        change_pin_ip=RateLimitRule("change_pin_ip", 10, MINUTE),
    )


@pytest.mark.parametrize(
    "text", ["677001122", "677 00 11 22", "+237677001122", "00237677001122", "237677001122"]
)
def test_every_spelling_of_a_number_shares_its_e164_key(text: str) -> None:
    assert phone_key(text, "203.0.113.7") == "+237677001122"


def test_invalid_inputs_share_one_key_per_ip() -> None:
    assert phone_key("pas-un-numero", "203.0.113.7") == "invalid@203.0.113.7"
    assert phone_key("12", "203.0.113.7") == "invalid@203.0.113.7"
    assert phone_key("abc", "") == "invalid@unknown"


def test_throttle_raises_rate_limited_with_whole_seconds() -> None:
    clock = FixedClock(T0)
    throttle = AuthThrottle(InMemoryRateLimiter(), clock, rules())
    throttle.check_login_phone("677001122", "a")
    clock.advance(timedelta(seconds=0.5))
    throttle.check_login_phone("+237 677 00 11 22", "b")
    with pytest.raises(RateLimited) as caught:
        throttle.check_login_phone("00237677001122", "c")
    # 15 min - 0,5 s, arrondi au supérieur.
    assert caught.value.retry_after == 900
    assert caught.value.details == {"retry_after": 900}
    assert caught.value.code == "RATE_LIMITED"


def test_rate_limited_needs_a_positive_wait() -> None:
    with pytest.raises(ValueError, match="seconde"):
        RateLimited(0)


def test_rules_are_validated() -> None:
    with pytest.raises(ValueError, match="limite"):
        RateLimitRule("x", 0, MINUTE)
    with pytest.raises(ValueError, match="fenêtre"):
        RateLimitRule("x", 1, timedelta(0))
    same = RateLimitRule("dup", 1, MINUTE)
    with pytest.raises(ValueError, match="double"):
        AuthRateRules(login_ip=same, login_phone=same, refresh_ip=same, change_pin_ip=same)
