"""Rotation du refresh (§ 8.1), réutilisation (SEC-R05), révocation, déconnexion volontaire."""

from datetime import timedelta

import pytest

from app.application.identity.sessions import SessionPolicy, format_refresh_token
from app.application.identity.use_cases.login import CredentialKind
from app.application.identity.use_cases.logout import Logout
from app.application.identity.use_cases.refresh_session import RefreshSession
from app.domain.identity.errors import AccountDisabled, SessionRevoked, Unauthenticated
from app.domain.identity.events import RevocationReason, SessionId, SessionRevokedEvent
from app.domain.shared.ids import DeviceId, UserId
from tests.application.identity.support import PASSWORD, T0, World


def refresh_uc(world: World) -> RefreshSession:
    return RefreshSession(
        world.uow_factory, world.secrets, world.issuer, world.clock, world.memberships
    )


def logout_uc(world: World) -> Logout:
    return Logout(world.uow_factory, world.secrets, world.clock)


def test_rotation_issues_a_new_refresh_and_slides_the_expiry() -> None:
    world = World()
    world.register()
    device = DeviceId.new()
    first = world.login(device=device)
    world.clock.advance(timedelta(minutes=14))
    second = refresh_uc(world).execute(first.refresh_token, device)
    assert second.session_id == first.session_id
    assert second.refresh_token != first.refresh_token
    assert second.refresh_expires_at == T0 + timedelta(minutes=14, days=30)
    assert world.identity(second, device).session_id == first.session_id


def test_reusing_a_rotated_token_revokes_only_that_session() -> None:
    world = World()
    world.register()
    d1, d2 = DeviceId.new(), DeviceId.new()
    first, other = world.login(device=d1), world.login(device=d2)
    second = refresh_uc(world).execute(first.refresh_token, d1)
    world.recorder.received.clear()
    with pytest.raises(SessionRevoked):
        refresh_uc(world).execute(first.refresh_token, d1)  # jeton déjà tourné
    with pytest.raises(SessionRevoked):
        refresh_uc(world).execute(second.refresh_token, d1)  # la victime aussi est déconnectée
    with pytest.raises(SessionRevoked):
        world.identity(second, d1)
    assert refresh_uc(world).execute(other.refresh_token, d2).access_token
    (event,) = world.recorder.received
    assert isinstance(event, SessionRevokedEvent)
    assert event.reason is RevocationReason.REFRESH_REUSE


def test_disabled_account_cannot_refresh() -> None:
    world = World()
    user = world.register()
    device = DeviceId.new()
    issued = world.login(device=device)
    stored = world.user(user)
    stored.disable(T0, by=UserId.new())
    world.save(stored)
    with pytest.raises(AccountDisabled):
        refresh_uc(world).execute(issued.refresh_token, device)
    with pytest.raises(AccountDisabled):
        world.identity(issued, device)


@pytest.mark.parametrize(
    "token",
    ["", "sans-separateur", "pas-un-uuid.secret", f"{SessionId.new()}.", f"{SessionId.new()}.x"],
)
def test_malformed_or_unknown_token_is_unauthenticated(token: str) -> None:
    world = World()
    with pytest.raises(Unauthenticated) as caught:
        refresh_uc(world).execute(token, DeviceId.new())
    assert caught.value.code == "UNAUTHENTICATED"


def test_token_presented_by_another_device_is_refused() -> None:
    world = World()
    world.register()
    issued = world.login(device=DeviceId.new())
    with pytest.raises(Unauthenticated):
        refresh_uc(world).execute(issued.refresh_token, DeviceId.new())


def test_expired_session_must_log_in_again() -> None:
    world = World(policy_settings=SessionPolicy(refresh_ttl=timedelta(days=1)))
    world.register()
    device = DeviceId.new()
    issued = world.login(device=device)
    world.clock.advance(timedelta(days=1))
    with pytest.raises(Unauthenticated) as caught:
        refresh_uc(world).execute(issued.refresh_token, device)
    assert caught.value.code == "UNAUTHENTICATED"
    assert world.login(device=device).session_id != issued.session_id


def test_admin_session_is_absolute_eight_hours() -> None:
    world = World()
    world.register("691234567", PASSWORD, admin=True)
    device = DeviceId.new()
    issued = world.login("691234567", PASSWORD, device=device, kind=CredentialKind.PASSWORD)
    world.clock.advance(timedelta(hours=7, minutes=50))
    later = refresh_uc(world).execute(issued.refresh_token, device)
    assert later.refresh_expires_at == T0 + timedelta(hours=8)
    assert later.access_expires_at == T0 + timedelta(hours=8)  # borné par la session
    world.clock.advance(timedelta(minutes=10))
    with pytest.raises(Unauthenticated):
        refresh_uc(world).execute(later.refresh_token, device)


def test_logout_revokes_the_session_and_is_idempotent() -> None:
    world = World()
    world.register()
    device = DeviceId.new()
    issued = world.login(device=device)
    logout_uc(world).execute(issued.refresh_token, device)
    logout_uc(world).execute(issued.refresh_token, device)
    with pytest.raises(SessionRevoked):
        refresh_uc(world).execute(issued.refresh_token, device)
    with pytest.raises(SessionRevoked):
        world.identity(issued, device)
    assert world.login(device=device).session_id != issued.session_id


def test_logout_with_a_stale_token_records_a_reuse() -> None:
    world = World()
    world.register()
    device = DeviceId.new()
    first = world.login(device=device)
    refresh_uc(world).execute(first.refresh_token, device)
    world.recorder.received.clear()
    logout_uc(world).execute(first.refresh_token, device)
    (event,) = world.recorder.received
    assert isinstance(event, SessionRevokedEvent)
    assert event.reason is RevocationReason.REFRESH_REUSE


def test_logout_of_an_unknown_session_is_unauthenticated() -> None:
    world = World()
    with pytest.raises(Unauthenticated):
        logout_uc(world).execute(format_refresh_token(SessionId.new(), "x"), DeviceId.new())
