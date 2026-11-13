"""Verdict du jeton présenté (specs § 8.1) : fenêtre de rejeu, autre appareil, révocation."""

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.identity.events import RevocationReason
from app.domain.identity.refresh_rotation import REFRESH_REPLAY_GRACE, RefreshVerdict
from app.domain.identity.session import DeviceSession
from app.domain.shared.errors import InvalidStateTransition
from app.domain.shared.ids import DeviceId, UserId

NOW = datetime(2026, 11, 13, 9, 0, tzinfo=UTC)
DAY = timedelta(days=1)
SECOND = timedelta(seconds=1)


def rotated_session() -> DeviceSession:
    """Session dont le jeton `h1` vient d'être remplacé par `h2` (successeur de `h1`)."""
    session = DeviceSession.open(
        user_id=UserId.new(),
        device_id=DeviceId.new(),
        device_label="Android — Chrome",
        refresh_hash="h1",
        now=NOW,
        lifetime=DAY,
        sliding=True,
    )
    session.rotate("h2", NOW, DAY)
    return session


def verdict(
    session: DeviceSession,
    presented: str,
    *,
    successor: str = "h2",
    device: DeviceId | None = None,
    at: datetime = NOW,
) -> RefreshVerdict:
    return session.judge_refresh(presented, successor, device or session.device_id, at)


def test_rotation_remembers_the_replaced_token_and_its_instant() -> None:
    session = rotated_session()
    assert (session.refresh_hash, session.previous_refresh_hash) == ("h2", "h1")
    assert session.rotated_at == NOW


def test_current_token_rotates() -> None:
    assert verdict(rotated_session(), "h2", successor="h3") is RefreshVerdict.CURRENT


@pytest.mark.parametrize("elapsed", [timedelta(0), SECOND, REFRESH_REPLAY_GRACE])
def test_just_replaced_token_inside_the_window_is_a_replay(elapsed: timedelta) -> None:
    assert verdict(rotated_session(), "h1", at=NOW + elapsed) is RefreshVerdict.REPLAY


def test_just_replaced_token_after_the_window_is_a_reuse() -> None:
    late = NOW + REFRESH_REPLAY_GRACE + SECOND
    assert verdict(rotated_session(), "h1", at=late) is RefreshVerdict.REUSE


def test_replay_must_lead_to_the_current_successor() -> None:
    # Le jeton remplacé ne mène pas (ou plus) au jeton actuel : aucune tolérance.
    assert verdict(rotated_session(), "h1", successor="autre") is RefreshVerdict.REUSE


def test_older_tokens_are_never_replays() -> None:
    session = rotated_session()
    session.rotate("h3", NOW + SECOND, DAY)  # h1 a deux générations de retard
    assert verdict(session, "h1", successor="h2", at=NOW + SECOND) is RefreshVerdict.REUSE
    assert verdict(session, "h2", successor="h3", at=NOW + SECOND) is RefreshVerdict.REPLAY


def test_unknown_secret_on_the_same_device_is_a_reuse() -> None:
    assert verdict(rotated_session(), "inconnu") is RefreshVerdict.REUSE


def test_replaced_token_from_another_device_is_a_reuse_even_inside_the_window() -> None:
    assert verdict(rotated_session(), "h1", device=DeviceId.new()) is RefreshVerdict.REUSE


@pytest.mark.parametrize("presented", ["h2", "inconnu"])
def test_other_device_without_a_stale_token_is_foreign(presented: str) -> None:
    session = rotated_session()
    assert verdict(session, presented, device=DeviceId.new()) is RefreshVerdict.FOREIGN


def test_new_login_on_the_device_forgets_the_replaced_token() -> None:
    session = rotated_session()
    session.reopen("h9", "Android — Chrome", NOW, DAY)
    assert (session.previous_refresh_hash, session.rotated_at) == (None, None)
    assert verdict(session, "h1", successor="h9") is RefreshVerdict.REUSE


def test_revoked_or_expired_session_has_no_verdict() -> None:
    session = rotated_session()
    with pytest.raises(InvalidStateTransition):
        verdict(session, "h2", at=NOW + DAY)
    session.revoke(NOW, RevocationReason.REFRESH_REUSE)
    with pytest.raises(InvalidStateTransition):
        verdict(session, "h1")
