"""Compteur propre à « Changer mon code » (décision client du 11/11/2026, T08 bis)."""

from datetime import timedelta

import pytest

from app.application.identity.ports import TemporaryPinGenerator
from app.application.identity.use_cases.authenticate import AuthenticatedUser
from app.application.identity.use_cases.change_pin import ChangePin, ChangePinCommand
from app.application.identity.use_cases.reset_pin import ResetPin
from app.application.security.actor import Actor
from app.application.security.roles import Role
from app.domain.identity.errors import CurrentPinInvalid, InvalidCredentials, PinChangeLocked
from app.domain.identity.events import LoginFailed, PinChangeFailed, PinChangeLockedEvent
from app.domain.identity.user import User, UserStatus
from app.domain.shared.ids import DeviceId
from tests.application.identity.support import PIN, SHOP, T0, World

NEW = "730518"
WRONG = ChangePinCommand(current="999111", new=NEW, confirmation=NEW)
RIGHT = ChangePinCommand(current=PIN, new=NEW, confirmation=NEW)


def open_session(world: World) -> tuple[User, AuthenticatedUser, str, ChangePin]:
    user = world.register()
    device = DeviceId.new()
    issued = world.login(device=device)
    identity = world.identity(issued, device)
    use_case = ChangePin(world.uow_factory, world.hasher, world.clock)
    return user, identity, issued.access_token, use_case


def fail(use_case: ChangePin, identity: AuthenticatedUser, times: int) -> None:
    for _ in range(times):
        with pytest.raises(CurrentPinInvalid):
            use_case.execute(identity, WRONG)


def test_wrong_current_code_is_422_with_remaining_attempts_never_401() -> None:
    world = World()
    _, identity, _, use_case = open_session(world)
    remaining = []
    for _ in range(5):
        with pytest.raises(CurrentPinInvalid) as caught:
            use_case.execute(identity, WRONG)
        assert caught.value.code == "CURRENT_PIN_INVALID"
        remaining.append(caught.value.details["remaining_attempts"])
    assert remaining == [4, 3, 2, 1, 0]  # le 5ᵉ pose le blocage ; l'appel suivant → 423
    with pytest.raises(PinChangeLocked):
        use_case.execute(identity, WRONG)


def test_four_wrong_then_right_resets_the_counter() -> None:
    world = World()
    user, identity, _, use_case = open_session(world)
    fail(use_case, identity, 4)
    assert world.user(user).pin_change_lockout.failures == 4
    use_case.execute(identity, RIGHT)
    assert world.user(user).pin_change_lockout.failures == 0


def test_five_wrong_lock_change_pin_only_for_fifteen_minutes() -> None:
    world = World()
    user, identity, token, use_case = open_session(world)
    world.recorder.received.clear()
    fail(use_case, identity, 5)
    until = T0 + timedelta(minutes=15)
    with pytest.raises(PinChangeLocked) as caught:
        use_case.execute(identity, RIGHT)  # même le bon code est refusé, sans être compté
    assert caught.value.code == "PIN_CHANGE_LOCKED"
    assert caught.value.details["until"] == until.isoformat()
    kinds = [type(event) for event in world.recorder.received]
    assert kinds == [PinChangeFailed] * 5 + [PinChangeLockedEvent]
    # le reste fonctionne : session ouverte, nouveau login, compteur du login intact
    assert world.authenticate.identify(token, identity.device_id).user_id == user.id
    device = DeviceId.new()
    assert world.identity(world.login(device=device), device).user_id == user.id
    stored = world.user(user)
    assert (stored.status, stored.failed_attempts) == (UserStatus.ACTIVE, 0)
    world.clock.move_to(until - timedelta(seconds=1))
    with pytest.raises(PinChangeLocked):
        use_case.execute(identity, RIGHT)
    world.clock.move_to(until)
    fail(use_case, identity, 1)
    assert world.user(user).pin_change_lockout.failures == 1  # repart de zéro
    use_case.execute(identity, RIGHT)


def test_counters_are_independent() -> None:
    world = World()
    user, identity, _, use_case = open_session(world)
    fail(use_case, identity, 3)
    assert world.user(user).failed_attempts == 0  # change-pin ne touche pas le login
    for _ in range(4):
        with pytest.raises(InvalidCredentials):
            world.login(secret="999111")
    world.login()  # remet le compteur du login à 0…
    stored = world.user(user)
    assert (stored.failed_attempts, stored.pin_change_lockout.failures) == (0, 3)  # …pas l'autre
    login_failures = [e for e in world.recorder.received if isinstance(e, LoginFailed)]
    assert len(login_failures) == 4


def test_login_lock_does_not_block_change_pin_from_an_open_session() -> None:
    world = World()
    user, identity, _, use_case = open_session(world)
    for _ in range(5):
        with pytest.raises(InvalidCredentials):
            world.login(secret="999111")
    assert world.user(user).status_at(world.clock.now()) is UserStatus.LOCKED
    use_case.execute(identity, RIGHT)
    assert world.user(user).pin_change_lockout.failures == 0


class FixedPin(TemporaryPinGenerator):
    def generate(self) -> str:
        return "531902"


def test_reset_pin_lifts_the_change_pin_lock() -> None:
    world = World()
    owner = world.register("670000001", role=Role.OWNER)
    user, identity, _, use_case = open_session(world)
    fail(use_case, identity, 5)
    actor = Actor.member(user_id=owner.id, device_id=DeviceId.new(), shop_id=SHOP, role=Role.OWNER)
    reset = ResetPin(world.uow_factory, world.access, world.hasher, FixedPin(), world.clock)
    assert reset.execute(actor, user.id) == "531902"
    assert world.user(user).pin_change_lockout.lock_end(world.clock.now()) is None
    use_case.execute(identity, ChangePinCommand(current="531902", new=NEW, confirmation=NEW))
