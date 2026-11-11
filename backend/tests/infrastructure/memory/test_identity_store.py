"""Unité de travail plateforme mémoire : cycle de vie, unicité du téléphone, concurrence."""

import pytest

from app.application.identity.ports import IdentityEventHandler
from app.application.identity.uow import IdentityUnitOfWork
from app.application.ports.errors import (
    UncommittedChanges,
    UnitOfWorkStateError,
    UnsavedChanges,
)
from app.application.security.roles import Role
from app.domain.identity.events import IdentityEvent
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.domain.shared.errors import Duplicate, NotFound, VersionConflict
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.infrastructure.persistence.memory.identity import (
    MemoryIdentityUnitOfWork,
    MemoryIdentityUnitOfWorkFactory,
)
from app.infrastructure.persistence.memory.memberships import InMemoryMembershipDirectory
from app.infrastructure.persistence.memory.platform_store import MemoryPlatformStore
from tests.application.identity.support import T0, RecordingHandler


def user(phone: str = "677001122") -> User:
    return User.register(phone=PhoneNumber.parse(phone), name="Awa", secret_hash="h")


def factory() -> MemoryIdentityUnitOfWorkFactory:
    return MemoryIdentityUnitOfWorkFactory(MemoryPlatformStore())


def stored(uow_factory: MemoryIdentityUnitOfWorkFactory, alice: User) -> User:
    with uow_factory() as uow:
        uow.users.add(alice)
        uow.commit()
    return alice


def test_phone_is_unique_across_the_platform_at_write_and_at_commit() -> None:
    uow_factory = factory()
    stored(uow_factory, user())
    with uow_factory() as uow, pytest.raises(Duplicate) as caught:
        uow.users.add(user("+237677001122"))
    assert caught.value.details["constraint"] == "user_phone"
    first, second = uow_factory(), uow_factory()
    with first, second:
        first.users.add(user("699000001"))
        second.users.add(user("699000001"))
        first.commit()
        with pytest.raises(Duplicate):
            second.commit()


def test_reads_are_copies_and_writes_stay_private_until_commit() -> None:
    uow_factory = factory()
    alice = stored(uow_factory, user())
    with uow_factory() as uow:
        loaded = uow.users.get(alice.id)
        loaded.name = "modifié sans update"
        assert uow.users.get(alice.id).name == "Awa"
        loaded.rehash("h2")
        uow.users.update(loaded)
        with uow_factory() as other:
            assert other.users.get(alice.id).secret_hash == "h"
        uow.commit()
    with uow_factory() as uow:
        assert uow.users.find_by_phone(alice.phone) is not None
        assert uow.users.find(UserId.new()) is None
        with pytest.raises(NotFound):
            uow.users.get(UserId.new())


def test_optimistic_lock_between_concurrent_units() -> None:
    uow_factory = factory()
    alice = stored(uow_factory, user())
    first, second = uow_factory(), uow_factory()
    with first, second:
        a, b = first.users.get(alice.id), second.users.get(alice.id)
        a.rehash("h-a")
        b.rehash("h-b")
        first.users.update(a)
        first.users.update(a)  # deux écritures dans la même transaction
        second.users.update(b)
        first.commit()
        with pytest.raises(VersionConflict):
            second.commit()
    with uow_factory() as uow:
        stale = uow.users.get(alice.id)
        stale.version = 1
        with pytest.raises(VersionConflict):
            uow.users.update(stale)


def test_lifecycle_guards() -> None:
    uow_factory = factory()
    with pytest.raises(UncommittedChanges), uow_factory() as uow:
        uow.users.add(user())
    uow = uow_factory()
    with pytest.raises(UnitOfWorkStateError):
        _ = uow.users
    with uow:
        uow.rollback()
        with pytest.raises(UnitOfWorkStateError):
            uow.commit()
    with pytest.raises(UnitOfWorkStateError, match="qu'une fois"), uow:
        pass

    def fail_inside() -> None:
        with uow_factory() as failing:
            failing.users.add(user("699000002"))
            msg = "boom"
            raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="boom"):
        fail_inside()
    with uow_factory() as uow:
        assert uow.users.find_by_phone(PhoneNumber.parse("699000002")) is None


def test_adapter_hooks_refuse_use_before_begin() -> None:
    uow = MemoryIdentityUnitOfWork(MemoryPlatformStore())
    for hook in (uow._users, uow._sessions, uow._has_pending_changes):
        with pytest.raises(UnitOfWorkStateError, match="non ouverte"):
            hook()  # primitive d'adaptateur appelée hors cycle : garde-fou testé


def test_version_rules_of_the_repository_template() -> None:
    uow_factory = factory()
    alice = stored(uow_factory, user())
    with uow_factory() as uow:
        with pytest.raises(ValueError, match="neuf"):
            uow.users.add(alice)
        with pytest.raises(ValueError, match="déjà enregistré"):
            uow.users.update(user("699000003"))
        with pytest.raises(Duplicate):
            uow.users.add(User(alice.id, PhoneNumber.parse("699000004"), "Clone", "h"))


def test_events_reach_handlers_and_unsaved_events_fail_the_commit() -> None:
    recorder = RecordingHandler()
    uow_factory = MemoryIdentityUnitOfWorkFactory(MemoryPlatformStore(), [recorder])
    alice = stored(uow_factory, user())
    with uow_factory() as uow:
        loaded = uow.users.get(alice.id)
        loaded.record_failed_attempt(T0, DeviceId.new())
        with pytest.raises(UnsavedChanges):
            uow.commit()
    assert recorder.received == []


def test_membership_directory() -> None:
    directory = InMemoryMembershipDirectory()
    user_id, shop = UserId.new(), ShopId.new()
    directory.grant(user_id, shop, "Motos Garoua", Role.OWNER)
    with pytest.raises(Duplicate):
        directory.grant(user_id, shop, "Motos Garoua", Role.SELLER)
    directory.set_active(user_id, shop, active=False)
    view = directory.find(user_id, shop)
    assert view is not None
    assert not view.active
    assert directory.find(UserId.new(), shop) is None
    with pytest.raises(KeyError):
        directory.set_active(UserId.new(), shop, active=True)


class EchoHandler(IdentityEventHandler):
    """Chaque événement en produit un nouveau : cascade sans fin, à stopper."""

    def handle(self, event: IdentityEvent, uow: IdentityUnitOfWork) -> None:
        echoed = uow.users.get(event.user_id)
        echoed.change_secret("h", T0)
        uow.users.update(echoed)


def test_endless_event_cascade_is_stopped_and_rolled_back() -> None:
    uow_factory = MemoryIdentityUnitOfWorkFactory(MemoryPlatformStore(), [EchoHandler()])
    with uow_factory() as uow:
        alice = user()
        alice.record_failed_attempt(T0, DeviceId.new())
        uow.users.add(alice)
        with pytest.raises(RuntimeError, match="cascade sans fin"):
            uow.commit()
    with uow_factory() as uow:
        assert uow.users.find(alice.id) is None
