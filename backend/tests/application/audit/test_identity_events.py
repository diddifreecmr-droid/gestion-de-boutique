"""Traduction des événements de l'identité en entrées de journal (Q-23, UC-JRN-03)."""

from datetime import timedelta

import pytest

from app.application.audit.identity_events import identity_audit_entries
from app.application.security.roles import Role
from app.domain.audit.events import UnauditedEvent
from app.domain.audit.values import AuditAction
from app.domain.identity import events as ev
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.infrastructure.persistence.memory.memberships import InMemoryMembershipDirectory
from tests.application.identity.support import T0

USER, OWNER = UserId.new(), UserId.new()
DEVICE, SESSION = DeviceId.new(), ev.SessionId.new()
SHOP_A, SHOP_B = ShopId.new(), ShopId.new()
LATER = T0 + timedelta(minutes=15)


@pytest.fixture
def directory() -> InMemoryMembershipDirectory:
    memberships = InMemoryMembershipDirectory()
    memberships.grant(USER, SHOP_A, "A", Role.SELLER)
    memberships.grant(USER, SHOP_B, "B", Role.ACCOUNTANT)
    memberships.grant(OWNER, SHOP_A, "A", Role.OWNER)
    return memberships


SELF_EVENTS = [
    (
        ev.LoginSucceeded(user_id=USER, occurred_at=T0, device_id=DEVICE, session_id=SESSION),
        AuditAction.LOGIN,
        False,
    ),
    (
        ev.LoginFailed(user_id=USER, occurred_at=T0, device_id=DEVICE, failed_attempts=2),
        AuditAction.LOGIN,
        False,
    ),
    (ev.UserLocked(user_id=USER, occurred_at=T0, locked_until=LATER), AuditAction.UPDATE, True),
    (ev.PinChanged(user_id=USER, occurred_at=T0), AuditAction.UPDATE, False),
    (
        ev.PinChangeFailed(user_id=USER, occurred_at=T0, device_id=DEVICE, failed_attempts=1),
        AuditAction.UPDATE,
        False,
    ),
    (
        ev.PinChangeLockedEvent(user_id=USER, occurred_at=T0, locked_until=LATER),
        AuditAction.UPDATE,
        True,
    ),
    (
        ev.SessionRevokedEvent(
            user_id=USER,
            occurred_at=T0,
            session_id=SESSION,
            device_id=DEVICE,
            reason=ev.RevocationReason.LOGOUT,
        ),
        AuditAction.LOGOUT,
        False,
    ),
]


@pytest.mark.parametrize(("event", "action", "sensitive"), SELF_EVENTS)
def test_self_actions_go_to_every_shop_of_the_user(
    directory: InMemoryMembershipDirectory,
    event: ev.IdentityEvent,
    action: AuditAction,
    sensitive: bool,
) -> None:
    entries = identity_audit_entries(event, directory, LATER)
    assert {e.shop_id for e in entries} == {SHOP_A, SHOP_B}
    roles = {e.shop_id: e.performer.role for e in entries}
    assert roles == {SHOP_A: "seller", SHOP_B: "accountant"}
    assert all(
        (e.action, e.sensitive, e.module) == (action, sensitive, "identity") for e in entries
    )
    assert all(e.entity.id == USER.value and e.captured_at == T0 for e in entries)


THIRD_PARTY = [
    ev.UserUnlocked(user_id=USER, occurred_at=T0, by=OWNER),
    ev.PinReset(user_id=USER, occurred_at=T0, by=OWNER),
    ev.UserDisabled(user_id=USER, occurred_at=T0, by=OWNER),
    ev.UserReactivated(user_id=USER, occurred_at=T0, by=OWNER),
    ev.SessionRevokedEvent(
        user_id=USER,
        occurred_at=T0,
        session_id=SESSION,
        device_id=DEVICE,
        reason=ev.RevocationReason.REMOTE,
        by=OWNER,
    ),
]


@pytest.mark.parametrize("event", THIRD_PARTY)
def test_owner_actions_go_only_to_shared_shops(
    directory: InMemoryMembershipDirectory, event: ev.IdentityEvent
) -> None:
    (written,) = identity_audit_entries(event, directory, LATER)
    assert written.shop_id == SHOP_A
    assert (written.performer.user_id, written.performer.role) == (OWNER, "owner")
    assert written.performer.device_id is None
    assert written.sensitive


def test_unknown_identity_event_is_refused(directory: InMemoryMembershipDirectory) -> None:
    class Unknown(ev.IdentityEvent):
        pass

    with pytest.raises(UnauditedEvent):
        identity_audit_entries(Unknown(user_id=USER, occurred_at=T0), directory, LATER)
