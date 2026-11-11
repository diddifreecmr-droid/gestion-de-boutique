"""Unité de travail mémoire et sa fabrique.

Les dépôts disponibles sont déclarés par la liste de leurs **classes d'adaptateur**, fournie par
la composition root (ou par les tests) : l'unité de travail ne grossit pas à chaque module. Le
port demandé est servi par l'unique adaptateur qui en hérite.
"""

from collections.abc import Sequence
from typing import Any

from app.application.ports.errors import UnitOfWorkStateError
from app.application.ports.event_handler import EventHandler
from app.application.ports.numbering import DocumentNumberAllocator
from app.application.ports.repository import Repository
from app.application.ports.uow import UnitOfWork
from app.domain.shared.ids import ShopId
from app.infrastructure.persistence.memory.database import MemoryDatabase
from app.infrastructure.persistence.memory.numbering import MemoryDocumentNumberAllocator
from app.infrastructure.persistence.memory.repository import MemoryRepository
from app.infrastructure.persistence.memory.transaction import MemoryTransaction

RepositoryRegistry = Sequence[type[MemoryRepository[Any, Any]]]


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

    def _build_repository(self, port: type[Repository[Any, Any]]) -> Repository[Any, Any]:
        candidates = [adapter for adapter in self._registry if issubclass(adapter, port)]
        if len(candidates) != 1:
            found = ", ".join(adapter.__name__ for adapter in candidates) or "aucun"
            msg = f"Il faut un et un seul adaptateur mémoire pour {port.__name__} ({found})"
            raise LookupError(msg)
        return candidates[0](self.shop_id, self, self._require_transaction())

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
