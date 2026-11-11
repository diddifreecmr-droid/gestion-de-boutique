"""Journalisation des refus d'accès (RG-D01) et décision Q-23 sur la boutique inscrite."""

import logging

import pytest

from app.application.audit.access_denied import RecordAccessDenied
from app.application.audit.ports import AuditLog, AuditQuery
from app.application.ports.pagination import PageRequest
from app.application.security.actor import Actor, AdminDelegation
from app.application.security.errors import (
    PermissionDenied,
    PlatformAdminRequired,
    ShopAccessDenied,
)
from app.application.security.permissions import Permission
from app.application.security.roles import Role
from app.bootstrap.persistence import MEMORY_REPOSITORIES
from app.domain.audit.entry import AuditEntry
from app.domain.audit.values import AuditAction
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.infrastructure.persistence.memory.clock import FixedClock
from app.infrastructure.persistence.memory.database import MemoryDatabase
from app.infrastructure.persistence.memory.uow import MemoryUnitOfWorkFactory
from tests.application.identity.support import T0

SHOP = ShopId.new()


@pytest.fixture
def factory() -> MemoryUnitOfWorkFactory:
    return MemoryUnitOfWorkFactory(MemoryDatabase(), MEMORY_REPOSITORIES)


def journal(factory: MemoryUnitOfWorkFactory) -> list[AuditEntry]:
    with factory(SHOP) as uow:
        return list(AuditLog.within(uow).search(AuditQuery(), PageRequest()).items)


def member() -> Actor:
    return Actor.member(
        user_id=UserId.new(), device_id=DeviceId.new(), shop_id=SHOP, role=Role.SELLER
    )


def admin(*, delegated: bool) -> Actor:
    delegation = AdminDelegation.granted_at(SHOP, T0) if delegated else None
    return Actor.platform_admin(
        user_id=UserId.new(), device_id=DeviceId.new(), shop_id=SHOP, delegation=delegation
    )


def test_member_refusal_is_written_in_the_shop(factory: MemoryUnitOfWorkFactory) -> None:
    actor = member()
    recorded = RecordAccessDenied(factory, FixedClock(T0))
    assert recorded.execute(PermissionDenied(actor, Permission.AUDIT_READ)) == SHOP
    (written,) = journal(factory)
    assert (written.action, written.performer.role, written.entity.number) == (
        AuditAction.ACCESS_DENIED,
        "seller",
        "AUDIT_READ",
    )
    assert written.performer.device_id == actor.device_id


def test_delegated_admin_refusal_is_written_in_the_shop(factory: MemoryUnitOfWorkFactory) -> None:
    error = PermissionDenied(admin(delegated=True), Permission.SALE_UPDATE)
    assert RecordAccessDenied(factory, FixedClock(T0)).execute(error) == SHOP
    assert journal(factory)[0].performer.role == "platform_admin"


@pytest.mark.parametrize(
    "error",
    [
        ShopAccessDenied(admin(delegated=False), Permission.SALE_READ),
        PlatformAdminRequired(member()),
        PermissionDenied(
            Actor.platform_admin(user_id=UserId.new(), device_id=DeviceId.new()),
            Permission.SALE_READ,
        ),
    ],
)
def test_other_refusals_go_to_the_platform_log(
    factory: MemoryUnitOfWorkFactory,
    error: PermissionDenied | ShopAccessDenied | PlatformAdminRequired,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="app.audit.platform"):
        assert RecordAccessDenied(factory, FixedClock(T0)).execute(error) is None
    assert "Accès refusé" in caplog.text
    assert journal(factory) == []


def test_anything_else_is_a_programming_error(factory: MemoryUnitOfWorkFactory) -> None:
    with pytest.raises(TypeError, match="Refus"):
        RecordAccessDenied(factory, FixedClock(T0)).execute(ValueError())  # type: ignore[arg-type]
