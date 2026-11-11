"""Agrégat `DeviceSession`, événements de l'identité et erreurs typées."""

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.identity.errors import AccountLocked
from app.domain.identity.events import (
    IdentityEvent,
    IdentityEvents,
    PinChanged,
    RevocationReason,
    SessionRevokedEvent,
)
from app.domain.identity.session import DeviceSession
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed
from app.domain.shared.ids import DeviceId, UserId

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)
DAY = timedelta(days=1)


def open_session(*, sliding: bool = True) -> DeviceSession:
    return DeviceSession.open(
        user_id=UserId.new(),
        device_id=DeviceId.new(),
        device_label="  Android   —  Chrome ",
        refresh_hash="h1",
        now=NOW,
        lifetime=DAY,
        sliding=sliding,
    )


def test_open_normalises_the_label_and_sets_expiry() -> None:
    session = open_session()
    assert session.device_label == "Android — Chrome"
    assert (session.created_at, session.last_seen, session.expires_at) == (NOW, NOW, NOW + DAY)
    assert session.is_active(NOW)
    assert not session.is_active(NOW + DAY)


@pytest.mark.parametrize("label", ["", "   ", "x" * 101])
def test_label_is_required_and_bounded(label: str) -> None:
    with pytest.raises(ValidationFailed):
        DeviceSession.open(
            user_id=UserId.new(),
            device_id=DeviceId.new(),
            device_label=label,
            refresh_hash="h",
            now=NOW,
            lifetime=DAY,
            sliding=True,
        )


def test_lifetime_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        open_session().rotate("h2", NOW, timedelta(0))


def test_rotation_slides_only_sliding_sessions() -> None:
    sliding, absolute = open_session(), open_session(sliding=False)
    later = NOW + timedelta(hours=2)
    for session in (sliding, absolute):
        session.rotate("h2", later, DAY)
        assert (session.matches("h2"), session.matches("h1"), session.last_seen) == (
            True,
            False,
            later,
        )
    assert (sliding.expires_at, absolute.expires_at) == (later + DAY, NOW + DAY)


def test_reopen_refreshes_label_and_expiry() -> None:
    session = open_session(sliding=False)
    session.reopen("h3", "iPhone — Safari", NOW + timedelta(hours=1), DAY)
    assert (session.device_label, session.expires_at) == (
        "iPhone — Safari",
        NOW + timedelta(hours=1) + DAY,
    )


def test_revocation_is_final_and_recorded() -> None:
    session = open_session()
    by = UserId.new()
    session.revoke(NOW, RevocationReason.REMOTE, by=by)
    assert session.revoked
    assert session.revoked_at == NOW
    assert not session.is_active(NOW)
    (event,) = session.events.pull()
    assert isinstance(event, SessionRevokedEvent)
    assert (event.reason, event.by, event.session_id) == (RevocationReason.REMOTE, by, session.id)
    with pytest.raises(InvalidStateTransition):
        session.revoke(NOW, RevocationReason.LOGOUT)
    with pytest.raises(InvalidStateTransition):
        session.rotate("h2", NOW, DAY)
    with pytest.raises(InvalidStateTransition):
        session.reopen("h2", "x", NOW, DAY)


def test_event_base_guards_and_collector() -> None:
    user_id = UserId.new()
    with pytest.raises(TypeError, match="abstraite"):
        IdentityEvent(user_id=user_id, occurred_at=NOW)
    with pytest.raises(TypeError, match="UserId"):
        PinChanged(user_id="x", occurred_at=NOW)  # type: ignore[arg-type]  # refus testé
    with pytest.raises(ValueError, match="naïf"):
        PinChanged(user_id=user_id, occurred_at=datetime(2026, 11, 11, 9, 0))
    events = IdentityEvents()
    first = PinChanged(user_id=user_id, occurred_at=NOW)
    events.record(first)
    assert (len(events), list(events)) == (1, [first])
    assert events.pull() == (first,)
    assert len(events) == 0
    with pytest.raises(TypeError, match="IdentityEvent"):
        events.record("pas un événement")  # type: ignore[arg-type]  # refus testé


def test_account_locked_carries_until_in_utc() -> None:
    error = AccountLocked(NOW)
    assert (error.code, error.details["until"]) == ("ACCOUNT_LOCKED", "2026-11-11T09:00:00+00:00")
