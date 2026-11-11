"""Unité de travail mémoire et sa fabrique (registre de dépôts : voir `persistence.registry`)."""

from collections.abc import Sequence
from typing import Any

from app.application.ports.errors import UnitOfWorkStateError
from app.application.ports.event_handler import EventHandler
from app.application.ports.numbering import DocumentNumberAllocator
from app.application.ports.shop_bound import ShopBoundPort
from app.application.ports.uow import UnitOfWork
from app.domain.shared.ids import ShopId
from app.infrastructure.persistence.memory.database import MemoryDatabase
from app.infrastructure.persistence.memory.numbering import MemoryDocumentNumberAllocator
from app.infrastructure.persistence.memory.repository import MemoryRepository
from app.infrastructure.persistence.memory.shop_store import MemoryShopStore
from app.infrastructure.persistence.memory.transaction import MemoryTransaction
from app.infrastructure.persistence.registry import select_adapter

MemoryAdapter = type[MemoryRepository[Any, Any]] | type[MemoryShopStore]
"""Adaptateur mémoire d'un port de boutique : dépôt d'agrégats ou port sans agrégat (journal)."""
RepositoryRegistry = Sequence[MemoryAdapter]


class MemoryUnitOfWork(UnitOfWork):
    """Unité de travail sur une `MemoryDatabase` partagée."""

    def __init__(
        self,
        database: MemoryDatabase,
        shop_id: ShopId,
        *,
        repositories: RepositoryRegistry,
        handlers: Sequence[EventHandler] = (),
    ) -> None:
        super().__init__(shop_id, handlers)
        self._database = database
        self._registry = tuple(repositories)
        self._transaction: MemoryTransaction | None = None
        self._allocator: MemoryDocumentNumberAllocator | None = None

    def _begin(self) -> None:
        self._transaction = MemoryTransaction(self._database, self.shop_id)
        self._allocator = MemoryDocumentNumberAllocator(self._transaction)

    def _commit(self) -> None:
        self._require_transaction().commit()

    def _rollback(self) -> None:
        self._require_transaction().discard()

    def _has_pending_changes(self) -> bool:
        return self._require_transaction().has_changes

    def _build_repository(self, port: type[ShopBoundPort]) -> ShopBoundPort:
        adapter = select_adapter(self._registry, port, "mémoire")
        return adapter(self.shop_id, self, self._require_transaction())

    def _numbering(self) -> DocumentNumberAllocator:
        if self._allocator is None:
            raise self._not_started()
        return self._allocator

    def _require_transaction(self) -> MemoryTransaction:
        if self._transaction is None:
            raise self._not_started()
        return self._transaction

    @staticmethod
    def _not_started() -> UnitOfWorkStateError:
        return UnitOfWorkStateError("Transaction mémoire non ouverte (utiliser `with`)")


class MemoryUnitOfWorkFactory:
    """`UnitOfWorkFactory` mémoire : une base partagée, un registre de dépôts, des handlers."""

    def __init__(
        self,
        database: MemoryDatabase,
        repositories: RepositoryRegistry,
        handlers: Sequence[EventHandler] = (),
    ) -> None:
        self._database = database
        self._repositories = tuple(repositories)
        self._handlers = tuple(handlers)

    def __call__(self, shop_id: ShopId) -> MemoryUnitOfWork:
        return MemoryUnitOfWork(
            self._database, shop_id, repositories=self._repositories, handlers=self._handlers
        )
