"""Agrégat `User` : blocage, déblocage, désactivation, secret, événements."""

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.identity.errors import AccountDisabled, AccountLocked, PinChangeRequired
from app.domain.identity.events import (
    PinChanged,
    PinReset,
    SessionId,
    UserDisabled,
    UserReactivated,
    UserUnlocked,
)
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import LOCK_DURATION, User, UserStatus
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed
from app.domain.shared.ids import DeviceId, UserId

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)
OWNER = UserId.new()
DEVICE = DeviceId.new()


def new_user() -> User:
    return User.register(phone=PhoneNumber.parse("677001122"), name="  Awa Bello ", secret_hash="h")


def locked_user() -> User:
    user = new_user()
    for _ in range(5):
        user.record_failed_attempt(NOW, DEVICE)
    return user


def test_registration_defaults() -> None:
    user = new_user()
    assert (user.name, user.must_change_pin, user.status, user.version) == (
        "Awa Bello",
        True,
        UserStatus.ACTIVE,
        0,
    )
    with pytest.raises(PinChangeRequired):
        user.ensure_pin_changed()


@pytest.mark.parametrize("name", ["", "   ", "x" * 121])
def test_name_is_required_and_bounded(name: str) -> None:
    with pytest.raises(ValidationFailed):
        User.register(phone=PhoneNumber.parse("677001122"), name=name, secret_hash="h")


def test_construction_guards() -> None:
    with pytest.raises(TypeError):
        User(UserId.new(), "677001122", "Awa", "h")  # type: ignore[arg-type]  # refus testé
    with pytest.raises(ValueError, match="empreinte"):
        User(UserId.new(), PhoneNumber.parse("677001122"), "Awa", "")
    with pytest.raises(ValueError, match="vide"):
        new_user().rehash("")


def test_lock_status_expires_with_time() -> None:
    user = locked_user()
    assert user.status_at(NOW) is UserStatus.LOCKED
    assert user.status_at(NOW + LOCK_DURATION) is UserStatus.ACTIVE
    with pytest.raises(AccountLocked) as caught:
        user.record_failed_attempt(NOW, DEVICE)
    assert caught.value.until == NOW + LOCK_DURATION
    with pytest.raises(AccountLocked):
        user.record_login(NOW, DEVICE, session_id=SessionId.new())


def test_unlock_by_owner() -> None:
    user = locked_user()
    user.events.pull()
    user.unlock(NOW, by=OWNER)
    assert (user.status, user.failed_attempts, user.locked_until) == (UserStatus.ACTIVE, 0, None)
    (event,) = user.events.pull()
    assert isinstance(event, UserUnlocked)
    assert event.by == OWNER
    with pytest.raises(InvalidStateTransition):
        user.unlock(NOW, by=OWNER)
    expired = locked_user()
    with pytest.raises(InvalidStateTransition):
        expired.unlock(NOW + LOCK_DURATION, by=OWNER)


def test_disable_and_reactivate() -> None:
    user = locked_user()
    user.events.pull()
    user.disable(NOW, by=OWNER)
    with pytest.raises(AccountDisabled):
        user.ensure_active()
    with pytest.raises(InvalidStateTransition):
        user.disable(NOW, by=OWNER)
    user.reset_secret("h2", NOW, by=OWNER)
    assert user.status is UserStatus.DISABLED  # un code provisoire ne réactive pas
    user.reactivate(NOW, by=OWNER)
    assert (user.status, user.failed_attempts, user.locked_until) == (UserStatus.ACTIVE, 0, None)
    with pytest.raises(InvalidStateTransition):
        user.reactivate(NOW, by=OWNER)
    kinds = [type(event) for event in user.events.pull()]
    assert kinds == [UserDisabled, PinReset, UserReactivated]


def test_change_and_reset_secret() -> None:
    user = locked_user()
    user.events.pull()
    user.reset_secret("provisoire", NOW + timedelta(minutes=1), by=OWNER)
    assert (user.secret_hash, user.must_change_pin, user.status) == (
        "provisoire",
        True,
        UserStatus.ACTIVE,
    )
    user.change_secret("nouveau", NOW)
    assert (user.secret_hash, user.must_change_pin) == ("nouveau", False)
    user.ensure_pin_changed()
    assert [type(e) for e in user.events.pull()] == [PinReset, PinChanged]
