"""Transaction mémoire plateforme : garde-fous de commit, d'absence et de fermeture."""

import copy

import pytest

from app.application.ports.errors import UnitOfWorkStateError
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.domain.shared.errors import Duplicate, NotFound
from app.infrastructure.persistence.memory.identity import MemoryIdentityUnitOfWorkFactory
from app.infrastructure.persistence.memory.platform_store import (
    MemoryPlatformStore,
    MemoryPlatformTransaction,
)


def user() -> User:
    return User.register(phone=PhoneNumber.parse("677001122"), name="Awa", secret_hash="h")


def test_same_id_inserted_by_two_transactions_fails_at_the_second_commit() -> None:
    uow_factory = MemoryIdentityUnitOfWorkFactory(MemoryPlatformStore())
    alice = user()
    twin = copy.deepcopy(alice)
    first, second = uow_factory(), uow_factory()
    with first, second:
        first.users.add(alice)
        second.users.add(twin)
        first.commit()
        with pytest.raises(Duplicate) as caught:
            second.commit()
    assert caught.value.details["constraint"] == "id"


def test_update_of_an_absent_user_is_not_found() -> None:
    uow_factory = MemoryIdentityUnitOfWorkFactory(MemoryPlatformStore())
    ghost = user()
    ghost.version = 1
    with uow_factory() as uow, pytest.raises(NotFound):
        uow.users.update(ghost)


def test_closed_transaction_refuses_every_access() -> None:
    transaction = MemoryPlatformTransaction(MemoryPlatformStore())
    transaction.commit()
    with pytest.raises(UnitOfWorkStateError, match="déjà validée"):
        transaction.visible("users")
