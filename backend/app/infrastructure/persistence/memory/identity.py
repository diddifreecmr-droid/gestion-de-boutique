"""Adaptateurs mémoire de l'identité : dépôts `User` / `DeviceSession` et unité de travail.

Comme les dépôts de boutique, les agrégats sont **copiés** à l'écriture et à la lecture
(`copy.deepcopy`) ; la copie stockée est purgée de ses événements en attente.
"""

import copy
from collections.abc import Hashable, Sequence
from typing import ClassVar, cast

from app.application.identity.ports import IdentityEventHandler
from app.application.identity.repositories import (
    DeviceSessionRepository,
    PlatformAggregate,
    PlatformRepository,
    PlatformTracker,
    UserRepository,
)
from app.application.identity.uow import IdentityUnitOfWork
from app.application.ports.errors import UnitOfWorkStateError
from app.domain.identity.events import SessionId
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.session import DeviceSession
from app.domain.identity.user import User
from app.domain.shared.ids import DeviceId, EntityId, UserId
from app.infrastructure.persistence.memory.platform_store import (
    MemoryPlatformStore,
    MemoryPlatformTransaction,
    PlatformRow,
)


class _MemoryPlatformRepository[IdT: EntityId, AggT: PlatformAggregate](
    PlatformRepository[IdT, AggT]
):
    table: ClassVar[str]

    def __init__(self, tracker: PlatformTracker, transaction: MemoryPlatformTransaction) -> None:
        super().__init__(tracker)
        self._transaction = transaction

    def _unique(self, aggregate: AggT) -> dict[str, Hashable]:
        return {}

    def _all(self) -> list[AggT]:
        # Les lignes de cette table ne sont construites que par `_row` à partir d'un AggT.
        rows = self._transaction.visible(self.table).values()
        return [cast(AggT, copy.deepcopy(row.payload)) for row in rows]

    def _load(self, entity_id: IdT) -> AggT | None:
        row = self._transaction.visible(self.table).get(entity_id)
        return None if row is None else cast(AggT, copy.deepcopy(row.payload))

    def _insert(self, aggregate: AggT) -> None:
        self._transaction.insert(self.table, self._row(aggregate))

    def _save(self, aggregate: AggT, *, expected_version: int) -> None:
        self._transaction.update(self.table, self._row(aggregate), expected_version)

    def _row(self, aggregate: AggT) -> PlatformRow:
        snapshot = copy.deepcopy(aggregate)
        snapshot.events.pull()
        return PlatformRow(aggregate.id, aggregate.version, self._unique(aggregate), snapshot)


class MemoryUserRepository(_MemoryPlatformRepository[UserId, User], UserRepository):
    table = "users"

    def _unique(self, aggregate: User) -> dict[str, Hashable]:
        return {"user_phone": aggregate.phone.e164}

    def find_by_phone(self, phone: PhoneNumber) -> User | None:
        matches = [user for user in self._all() if user.phone == phone]
        return self._tracked(matches)[0] if matches else None


class MemoryDeviceSessionRepository(
    _MemoryPlatformRepository[SessionId, DeviceSession], DeviceSessionRepository
):
    table = "device_sessions"

    def for_user(self, user_id: UserId) -> list[DeviceSession]:
        sessions = [s for s in self._all() if s.user_id == user_id]
        return self._tracked(sorted(sessions, key=lambda s: (s.created_at, s.id)))

    def active_for_device(self, user_id: UserId, device_id: DeviceId) -> DeviceSession | None:
        candidates = [
            s for s in self.for_user(user_id) if s.device_id == device_id and not s.revoked
        ]
        return candidates[-1] if candidates else None


class MemoryIdentityUnitOfWork(IdentityUnitOfWork):
    def __init__(
        self, store: MemoryPlatformStore, handlers: Sequence[IdentityEventHandler] = ()
    ) -> None:
        super().__init__(handlers)
        self._store = store
        self._transaction: MemoryPlatformTransaction | None = None
        self._user_repository: MemoryUserRepository | None = None
        self._session_repository: MemoryDeviceSessionRepository | None = None

    def _begin(self) -> None:
        self._transaction = MemoryPlatformTransaction(self._store)
        self._user_repository = MemoryUserRepository(self, self._transaction)
        self._session_repository = MemoryDeviceSessionRepository(self, self._transaction)

    def _commit(self) -> None:
        self._require_transaction().commit()

    def _rollback(self) -> None:
        self._require_transaction().discard()

    def _has_pending_changes(self) -> bool:
        return self._require_transaction().has_changes

    def _users(self) -> UserRepository:
        if self._user_repository is None:
            raise self._not_started()
        return self._user_repository

    def _sessions(self) -> DeviceSessionRepository:
        if self._session_repository is None:
            raise self._not_started()
        return self._session_repository

    def _require_transaction(self) -> MemoryPlatformTransaction:
        if self._transaction is None:
            raise self._not_started()
        return self._transaction

    @staticmethod
    def _not_started() -> UnitOfWorkStateError:
        return UnitOfWorkStateError("Transaction mémoire plateforme non ouverte (utiliser `with`)")


class MemoryIdentityUnitOfWorkFactory:
    """`IdentityUnitOfWorkFactory` mémoire : un stockage partagé, des handlers."""

    def __init__(
        self, store: MemoryPlatformStore, handlers: Sequence[IdentityEventHandler] = ()
    ) -> None:
        self._store = store
        self._handlers = tuple(handlers)

    def __call__(self) -> MemoryIdentityUnitOfWork:
        return MemoryIdentityUnitOfWork(self._store, self._handlers)
