"""`LockoutCounter` : compteur d'essais faux réutilisé par le login et le changement de code."""

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.identity.lockout import LOCK_DURATION, LockoutCounter
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User, UserStatus
from app.domain.shared.ids import DeviceId, UserId

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)


def test_fifth_failure_locks_and_expired_lock_restarts_from_zero() -> None:
    counter = LockoutCounter()
    for _ in range(4):
        counter = counter.after_failure(NOW)
    assert counter == LockoutCounter(4)
    counter = counter.after_failure(NOW)
    assert counter.locked_until == NOW + LOCK_DURATION
    assert counter.lock_end(NOW + LOCK_DURATION - timedelta(seconds=1)) == NOW + LOCK_DURATION
    assert counter.lock_end(NOW + LOCK_DURATION) is None
    assert counter.released(NOW) is counter
    assert counter.released(NOW + LOCK_DURATION) == LockoutCounter()
    assert counter.after_failure(NOW + LOCK_DURATION) == LockoutCounter(1)


def test_failure_during_a_lock_is_a_programming_error() -> None:
    locked = LockoutCounter(5, NOW + LOCK_DURATION)
    with pytest.raises(ValueError, match="pendant un blocage"):
        locked.after_failure(NOW)


def test_can_lock_false_only_counts() -> None:
    assert LockoutCounter(4).after_failure(NOW, can_lock=False) == LockoutCounter(5)


@pytest.mark.parametrize("failures", [-1, True, "1"])
def test_invalid_counts_are_refused(failures: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        LockoutCounter(failures)  # type: ignore[arg-type]  # refus testé à l'exécution


def test_naive_lock_end_is_refused() -> None:
    with pytest.raises(ValueError, match="naïf"):
        LockoutCounter(5, datetime(2026, 11, 11, 9, 0))


def test_account_disabled_during_a_login_lock_keeps_counting_without_error() -> None:
    user = User.register(phone=PhoneNumber.parse("677001122"), name="Awa", secret_hash="h")
    for _ in range(5):
        user.record_failed_attempt(NOW, DeviceId.new())
    user.disable(NOW, by=UserId.new())
    user.record_failed_attempt(NOW, DeviceId.new())
    assert (user.status, user.failed_attempts, user.locked_until) == (UserStatus.DISABLED, 6, None)
