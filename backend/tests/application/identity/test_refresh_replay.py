"""Réponse de rafraîchissement perdue (audit du 2026-11-13) : rejeu toléré, vol toujours détecté."""

from datetime import timedelta

import pytest

from app.application.identity.sessions import IssuedSession
from app.domain.identity.errors import AccountDisabled, SessionRevoked, Unauthenticated
from app.domain.identity.events import RevocationReason, SessionRevokedEvent
from app.domain.identity.refresh_rotation import REFRESH_REPLAY_GRACE
from app.domain.shared.ids import DeviceId, UserId
from tests.application.identity.support import T0, World
from tests.application.identity.test_refresh_logout import refresh_uc

SECOND = timedelta(seconds=1)


def lost_response(world: World, device: DeviceId) -> tuple[IssuedSession, IssuedSession]:
    """Connexion puis un rafraîchissement dont le client n'a jamais reçu la réponse."""
    world.register()
    first = world.login(device=device)
    world.clock.advance(timedelta(minutes=15))
    lost = refresh_uc(world).execute(first.refresh_token, device)
    world.recorder.received.clear()
    return first, lost


def session_version(world: World, issued: IssuedSession) -> int:
    with world.uow_factory() as uow:
        return uow.sessions.get(issued.session_id).version


def test_replay_inside_the_window_returns_the_same_successor_without_writing() -> None:
    world, device = World(), DeviceId.new()
    first, lost = lost_response(world, device)
    version = session_version(world, lost)
    world.clock.advance(REFRESH_REPLAY_GRACE)
    again = refresh_uc(world).execute(first.refresh_token, device)
    assert again.refresh_token == lost.refresh_token
    assert again.refresh_expires_at == lost.refresh_expires_at  # la fenêtre ne glisse pas
    assert world.identity(again, device).session_id == first.session_id
    assert session_version(world, lost) == version
    assert world.recorder.received == []  # pas d'alerte de sécurité
    # Le successeur reçu fonctionne ensuite normalement.
    assert refresh_uc(world).execute(again.refresh_token, device).access_token


def test_concurrent_style_double_replay_keeps_the_session() -> None:
    world, device = World(), DeviceId.new()
    first, lost = lost_response(world, device)
    tokens = {refresh_uc(world).execute(first.refresh_token, device).refresh_token for _ in "ab"}
    assert tokens == {lost.refresh_token}


def test_replay_after_the_window_revokes_and_is_journaled() -> None:
    world, device = World(), DeviceId.new()
    first, lost = lost_response(world, device)
    world.clock.advance(REFRESH_REPLAY_GRACE + SECOND)
    with pytest.raises(SessionRevoked):
        refresh_uc(world).execute(first.refresh_token, device)
    with pytest.raises(SessionRevoked):
        refresh_uc(world).execute(lost.refresh_token, device)
    (event,) = world.recorder.received
    assert isinstance(event, SessionRevokedEvent)
    assert event.reason is RevocationReason.REFRESH_REUSE


def test_replays_do_not_extend_the_window() -> None:
    world, device = World(), DeviceId.new()
    first, _ = lost_response(world, device)
    world.clock.advance(REFRESH_REPLAY_GRACE - SECOND)
    refresh_uc(world).execute(first.refresh_token, device)
    world.clock.advance(2 * SECOND)
    with pytest.raises(SessionRevoked):
        refresh_uc(world).execute(first.refresh_token, device)


def test_replaced_token_from_another_device_revokes_even_inside_the_window() -> None:
    world, device = World(), DeviceId.new()
    first, lost = lost_response(world, device)
    with pytest.raises(SessionRevoked):
        refresh_uc(world).execute(first.refresh_token, DeviceId.new())
    with pytest.raises(SessionRevoked):
        refresh_uc(world).execute(lost.refresh_token, device)
    (event,) = world.recorder.received
    assert isinstance(event, SessionRevokedEvent)
    assert event.reason is RevocationReason.REFRESH_REUSE


def test_current_token_from_another_device_is_still_a_plain_refusal() -> None:
    world, device = World(), DeviceId.new()
    _, lost = lost_response(world, device)
    with pytest.raises(Unauthenticated) as caught:
        refresh_uc(world).execute(lost.refresh_token, DeviceId.new())
    assert caught.value.code == "UNAUTHENTICATED"
    assert world.recorder.received == []
    assert refresh_uc(world).execute(lost.refresh_token, device).access_token


def test_revoked_session_is_never_replayed() -> None:
    world, device = World(), DeviceId.new()
    first, lost = lost_response(world, device)
    with world.uow_factory() as uow:
        session = uow.sessions.get(lost.session_id)
        session.revoke(T0, RevocationReason.REMOTE)
        uow.sessions.update(session)
        uow.commit()
    with pytest.raises(SessionRevoked):
        refresh_uc(world).execute(first.refresh_token, device)


def test_disabled_account_cannot_replay() -> None:
    world, device = World(), DeviceId.new()
    first, lost = lost_response(world, device)
    with world.uow_factory() as uow:
        stored = uow.users.get(lost.user_id)
    stored.disable(T0, by=UserId.new())
    world.save(stored)
    with pytest.raises(AccountDisabled):
        refresh_uc(world).execute(first.refresh_token, device)
