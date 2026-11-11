"""UC-SOC-02 — connexion : blocage (SEC-L01 à L08), désactivation (SEC-X01), admin (§ 15.1)."""

from datetime import timedelta

import pytest

from app.application.identity.use_cases.login import CredentialKind
from app.domain.identity.errors import (
    INVALID_CREDENTIALS_MESSAGE,
    AccountDisabled,
    AccountLocked,
    InvalidCredentials,
)
from app.domain.identity.events import LoginFailed, LoginSucceeded, UserLocked
from app.domain.identity.user import UserStatus
from app.domain.shared.ids import DeviceId, UserId
from tests.application.identity.support import PASSWORD, PIN, T0, FakeHasher, World

WRONG = "000001"


def fail(world: World, times: int, phone: str = "677001122") -> None:
    for _ in range(times):
        with pytest.raises(InvalidCredentials):
            world.login(phone, WRONG)


def test_success_issues_tokens_and_resets_counter() -> None:
    world = World()
    user = world.register()
    fail(world, 2)
    issued = world.login()
    assert issued.user_id == user.id
    assert issued.access_expires_at == T0 + timedelta(minutes=15)
    assert issued.refresh_expires_at == T0 + timedelta(days=30)
    assert not issued.must_change_pin
    stored = world.user(user)
    assert stored.failed_attempts == 0
    assert stored.last_login_at == T0


def test_any_phone_format_finds_the_same_account() -> None:
    world = World()
    world.register("+237 6 77 00 11 22")
    for phone in ("677001122", "237677001122", "00237677001122", "+237-677-00-11-22"):
        assert world.login(phone).access_token


@pytest.mark.parametrize("phone", ["699999999", "pas-un-numéro", "12"])
def test_unknown_or_malformed_phone_gets_the_generic_message(phone: str) -> None:
    world = World()
    world.register()
    with pytest.raises(InvalidCredentials) as caught:
        world.login(phone, PIN)
    assert caught.value.message == INVALID_CREDENTIALS_MESSAGE
    assert caught.value.code == "UNAUTHENTICATED"


def test_fifth_failure_locks_for_fifteen_minutes() -> None:
    world = World()
    user = world.register()
    fail(world, 4)
    assert world.user(user).status is UserStatus.ACTIVE
    t5 = world.clock.advance(timedelta(minutes=1))
    fail(world, 1)
    stored = world.user(user)
    assert (stored.status, stored.locked_until) == (UserStatus.LOCKED, t5 + timedelta(minutes=15))
    for offset in (timedelta(seconds=1), timedelta(minutes=14, seconds=59)):
        world.clock.move_to(t5 + offset)
        with pytest.raises(AccountLocked) as caught:
            world.login()
        assert caught.value.details["until"] == (t5 + timedelta(minutes=15)).isoformat()
    world.clock.move_to(t5 + timedelta(minutes=15))
    assert world.login().access_token
    assert world.user(user).failed_attempts == 0


def test_wrong_code_during_lock_is_also_423_and_not_counted() -> None:
    world = World()
    user = world.register()
    fail(world, 5)
    with pytest.raises(AccountLocked):
        world.login(secret=WRONG)
    assert world.user(user).failed_attempts == 5


def test_failure_after_lock_expiry_restarts_the_counter() -> None:
    world = World()
    user = world.register()
    fail(world, 5)
    world.clock.advance(timedelta(minutes=15))
    fail(world, 1)
    assert (world.user(user).status, world.user(user).failed_attempts) == (UserStatus.ACTIVE, 1)


def test_success_between_failures_never_locks() -> None:
    world = World()
    user = world.register()
    fail(world, 4)
    world.login()
    fail(world, 4)
    assert world.user(user).status is UserStatus.ACTIVE


def test_disabled_account_is_refused_only_after_a_correct_code() -> None:
    world = World()
    user = world.register()
    stored = world.user(user)
    stored.disable(T0, by=UserId.new())
    world.save(stored)
    with pytest.raises(InvalidCredentials):
        world.login(secret=WRONG)
    with pytest.raises(AccountDisabled) as caught:
        world.login()
    assert caught.value.message == "Compte désactivé, contactez le propriétaire"


def test_first_login_reports_must_change_pin() -> None:
    world = World()
    world.register(must_change=True)
    assert world.login().must_change_pin


def test_platform_admin_uses_a_password_and_gets_an_8_hour_session() -> None:
    world = World()
    world.register("691234567", PASSWORD, admin=True)
    with pytest.raises(InvalidCredentials):
        world.login("691234567", PASSWORD, kind=CredentialKind.PIN)
    issued = world.login("691234567", PASSWORD, kind=CredentialKind.PASSWORD)
    assert issued.is_platform_admin
    assert issued.refresh_expires_at == T0 + timedelta(hours=8)


def test_member_cannot_log_in_with_the_password_kind() -> None:
    world = World()
    world.register()
    with pytest.raises(InvalidCredentials):
        world.login(secret=PIN, kind=CredentialKind.PASSWORD)


def test_same_device_reuses_its_session_and_other_devices_get_their_own() -> None:
    world = World()
    world.register()
    device = DeviceId.new()
    first = world.login(device=device)
    world.clock.advance(timedelta(hours=1))
    again = world.login(device=device)
    other = world.login(device=DeviceId.new())
    assert again.session_id == first.session_id
    assert again.refresh_expires_at == T0 + timedelta(hours=1, days=30)
    assert other.session_id != first.session_id


def test_weak_hash_is_upgraded_at_login() -> None:
    world = World(hasher=FakeHasher(version="v2"))
    user = world.register()
    stored = world.user(user)
    stored.rehash("fake$v1$" + PIN)
    world.save(stored)
    world.login()
    assert world.user(user).secret_hash == "fake$v2$" + PIN


def test_events_are_recorded_for_the_journal() -> None:
    world = World()
    user = world.register()
    world.recorder.received.clear()
    fail(world, 5)
    world.clock.advance(timedelta(minutes=15))
    world.login()
    received = world.recorder.received
    kinds = [type(event) for event in received]
    assert kinds == [LoginFailed] * 5 + [UserLocked, LoginSucceeded]
    assert all(event.user_id == user.id for event in received)
