"""Unité de travail mémoire **plateforme** (identité, comptes commerçants) et sa fabrique.

Dépôts : `platform_repositories.py`. Avec un `ShopJoin`, l'unité peut joindre des unités de
boutique (`join_shop`) : leurs écritures sont validées **avec** les siennes, d'un bloc
(`joined.py`). Sans `ShopJoin`, `join_shop` lève `LookupError` (configuration incomplète).
"""

from collections.abc import Sequence

from app.application.identity.ports import IdentityEventHandler
from app.application.identity.repositories import (
    DeviceSessionRepository,
    MerchantAccountRepository,
    UserRepository,
)
from app.application.identity.uow import IdentityUnitOfWork
from app.application.ports.errors import UnitOfWorkStateError
from app.application.ports.uow import UnitOfWork
from app.domain.shared.ids import ShopId
from app.infrastructure.persistence.memory.joined import (
    JoinedMemoryUnitOfWork,
    ShopJoin,
    apply_jointly,
    require_alive,
)
from app.infrastructure.persistence.memory.platform_repositories import (
    MemoryDeviceSessionRepository,
    MemoryMerchantAccountRepository,
    MemoryUserRepository,
)
from app.infrastructure.persistence.memory.platform_store import (
    MemoryPlatformStore,
    MemoryPlatformTransaction,
)
from app.infrastructure.persistence.memory.transaction import MemoryTransaction

__all__ = [
    "MemoryDeviceSessionRepository",
    "MemoryIdentityUnitOfWork",
    "MemoryIdentityUnitOfWorkFactory",
    "MemoryUserRepository",
]


class MemoryIdentityUnitOfWork(IdentityUnitOfWork):
    def __init__(
        self,
        store: MemoryPlatformStore,
        handlers: Sequence[IdentityEventHandler] = (),
        join: ShopJoin | None = None,
    ) -> None:
        super().__init__(handlers)
        self._store = store
        self._join = join
        self._transaction: MemoryPlatformTransaction | None = None
        self._joined: list[MemoryTransaction] = []
        self._doomed = False
        self._repositories: (
            tuple[
                MemoryUserRepository, MemoryDeviceSessionRepository, MemoryMerchantAccountRepository
            ]
            | None
        ) = None

    def _begin(self) -> None:
        self._transaction = MemoryPlatformTransaction(self._store)
        self._repositories = (
            MemoryUserRepository(self, self._transaction),
            MemoryDeviceSessionRepository(self, self._transaction),
            MemoryMerchantAccountRepository(self, self._transaction),
        )

    def _commit(self) -> None:
        require_alive(self._doomed)
        writes = self._require_transaction().detach()
        if not any(transaction.is_open for transaction in self._joined):
            self._store.apply(writes)
            return
        if self._join is None:  # impossible : join_shop l'exige
            msg = "Unités jointes sans ShopJoin"
            raise RuntimeError(msg)
        # Une unité jointe en lecture seule a déjà fermé (jeté) sa transaction vide.
        changes = [transaction.detach() for transaction in self._joined if transaction.is_open]
        apply_jointly(self._join.database, self._store, changes, writes)

    def _rollback(self) -> None:
        self._require_transaction().discard()
        for transaction in self._joined:
            transaction.discard()

    def _has_pending_changes(self) -> bool:
        return self._require_transaction().has_changes or any(
            transaction.has_changes for transaction in self._joined
        )

    def _users(self) -> UserRepository:
        return self._require_repositories()[0]

    def _sessions(self) -> DeviceSessionRepository:
        return self._require_repositories()[1]

    def _merchants(self) -> MerchantAccountRepository:
        return self._require_repositories()[2]

    def _join_shop(self, shop_id: ShopId) -> UnitOfWork:
        if self._join is None:
            msg = "Unité plateforme sans ShopJoin : impossible de joindre une boutique"
            raise LookupError(msg)
        require_alive(self._doomed)
        return JoinedMemoryUnitOfWork(self._join, shop_id, self)

    # ------------------------------------------------------------------ hôte des unités jointes
    def enlist(self, transaction: MemoryTransaction) -> None:
        self._joined.append(transaction)

    def doom(self) -> None:
        self._doomed = True

    def _require_repositories(
        self,
    ) -> tuple[
        MemoryUserRepository, MemoryDeviceSessionRepository, MemoryMerchantAccountRepository
    ]:
        if self._repositories is None:
            raise self._not_started()
        return self._repositories

    def _require_transaction(self) -> MemoryPlatformTransaction:
        if self._transaction is None:
            raise self._not_started()
        return self._transaction

    @staticmethod
    def _not_started() -> UnitOfWorkStateError:
        return UnitOfWorkStateError("Transaction mémoire plateforme non ouverte (utiliser `with`)")


class MemoryIdentityUnitOfWorkFactory:
    """`IdentityUnitOfWorkFactory` mémoire : un stockage partagé, des handlers, une jointure."""

    def __init__(
        self,
        store: MemoryPlatformStore,
        handlers: Sequence[IdentityEventHandler] = (),
        join: ShopJoin | None = None,
    ) -> None:
        self._store = store
        self._handlers = tuple(handlers)
        self._join = join

    def __call__(self) -> MemoryIdentityUnitOfWork:
        return MemoryIdentityUnitOfWork(self._store, self._handlers, self._join)
