"""UC-SOC-07 — changer son code (recette PIN-01, PIN-02) ; mot de passe admin (§ 15.1)."""

from datetime import timedelta

import pytest

from app.application.identity.use_cases.change_pin import ChangePin, ChangePinCommand
from app.application.identity.use_cases.login import CredentialKind
from app.domain.identity.errors import (
    AccountLocked,
    InvalidCredentials,
    PasswordTooWeak,
    PinTooSimple,
)
from app.domain.identity.user import User
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import DeviceId
from tests.application.identity.support import PASSWORD, PIN, World

NEW = "730518"


def change(
    world: World, user: User, current: str, new: str, confirmation: str | None = None
) -> None:
    device = DeviceId.new()
    secret = PASSWORD if user.is_platform_admin else PIN
    kind = CredentialKind.PASSWORD if user.is_platform_admin else CredentialKind.PIN
    issued = world.login(user.phone.e164, secret, device=device, kind=kind)
    command = ChangePinCommand(current=current, new=new, confirmation=confirmation or new)
    ChangePin(world.uow_factory, world.hasher, world.clock).execute(
        world.identity(issued, device), command
    )


def test_first_login_change_clears_must_change_pin() -> None:
    world = World()
    user = world.register(must_change=True)
    change(world, user, PIN, NEW)
    stored = world.user(user)
    assert not stored.must_change_pin
    assert world.hasher.verify(stored.secret_hash, NEW)
    assert not world.login(secret=NEW).must_change_pin


@pytest.mark.parametrize("simple", ["123456", "654321", "000000", "111111", "121212"])
def test_simple_codes_are_refused(simple: str) -> None:
    world = World()
    user = world.register(must_change=True)
    with pytest.raises(PinTooSimple):
        change(world, user, PIN, simple)
    assert world.user(user).must_change_pin


def test_confirmation_must_match() -> None:
    world = World()
    user = world.register()
    with pytest.raises(ValidationFailed) as caught:
        change(world, user, PIN, NEW, confirmation="730519")
    assert caught.value.details["field"] == "new_pin_confirmation"


def test_new_code_must_differ_from_current() -> None:
    world = World()
    user = world.register()
    with pytest.raises(ValidationFailed) as caught:
        change(world, user, PIN, PIN)
    assert caught.value.details["field"] == "new_pin"


def test_malformed_new_code_is_a_validation_error() -> None:
    world = World()
    user = world.register()
    with pytest.raises(ValidationFailed):
        change(world, user, PIN, "12345a")


def test_wrong_current_code_counts_as_a_failed_attempt_up_to_the_lock() -> None:
    world = World()
    user = world.register()
    device = DeviceId.new()
    identity = world.identity(world.login(device=device), device)
    use_case = ChangePin(world.uow_factory, world.hasher, world.clock)
    wrong = ChangePinCommand(current="999111", new=NEW, confirmation=NEW)
    for _ in range(4):
        with pytest.raises(InvalidCredentials):
            use_case.execute(identity, wrong)
    assert world.user(user).failed_attempts == 4
    with pytest.raises(InvalidCredentials):
        use_case.execute(identity, wrong)
    right = ChangePinCommand(current=PIN, new=NEW, confirmation=NEW)
    with pytest.raises(AccountLocked):
        use_case.execute(identity, right)
    world.clock.advance(timedelta(minutes=15))
    use_case.execute(identity, right)
    assert world.hasher.verify(world.user(user).secret_hash, NEW)


def test_admin_changes_a_password_under_the_password_policy() -> None:
    world = World()
    admin = world.register("691234567", PASSWORD, admin=True)
    with pytest.raises(PasswordTooWeak):
        change(world, admin, PASSWORD, "court")
    change(world, admin, PASSWORD, "Une phrase de passe bien longue")
    assert world.hasher.verify(world.user(admin).secret_hash, "Une phrase de passe bien longue")
