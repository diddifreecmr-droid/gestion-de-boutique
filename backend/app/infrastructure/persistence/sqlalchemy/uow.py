"""Unité de travail SQL et sa fabrique : mêmes règles de cycle de vie que l'adaptateur mémoire.

Le cycle de vie (commit unique, rollback automatique, `UncommittedChanges`, remise des
événements) est entièrement dans le gabarit `UnitOfWork` ; cet adaptateur ne fournit que la
transaction : une connexion du pool, ouverte à l'entrée du `with`, rendue à la sortie.
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from app.application.ports.errors import UnitOfWorkStateError
from app.application.ports.event_handler import EventHandler
from app.application.ports.numbering import DocumentNumberAllocator
from app.application.ports.repository import Repository
from app.application.ports.uow import UnitOfWork
from app.domain.shared.ids import ShopId
from app.infrastructure.persistence.registry import select_adapter
from app.infrastructure.persistence.sqlalchemy.numbering import SqlDocumentNumberAllocator
from app.infrastructure.persistence.sqlalchemy.repository import SqlRepository
from app.infrastructure.persistence.sqlalchemy.transaction import SqlTransaction

SqlRepositoryRegistry = Sequence[type[SqlRepository[Any, Any]]]


class SqlUnitOfWork(UnitOfWork):
    """Unité de travail sur un moteur SQLAlchemy partagé."""

    def __init__(
        self,
        engine: sa.Engine,
        shop_id: ShopId,
        *,
        repositories: SqlRepositoryRegistry,
        handlers: Sequence[EventHandler] = (),
    ) -> None:
        super().__init__(shop_id, handlers)
        self._engine = engine
        self._registry = tuple(repositories)
        self._transaction: SqlTransaction | None = None
        self._allocator: SqlDocumentNumberAllocator | None = None

    def _begin(self) -> None:
        self._transaction = SqlTransaction(self._engine)
        self._allocator = SqlDocumentNumberAllocator(self._transaction, self.shop_id)

    def _commit(self) -> None:
        self._require_transaction().commit()

    def _rollback(self) -> None:
        self._require_transaction().discard()

    def _has_pending_changes(self) -> bool:
        return self._require_transaction().has_changes

    def _build_repository(self, port: type[Repository[Any, Any]]) -> Repository[Any, Any]:
        adapter = select_adapter(self._registry, port, "SQL")
        return adapter(self.shop_id, self, self._require_transaction())

    def _numbering(self) -> DocumentNumberAllocator:
        if self._allocator is None:
            raise self._not_started()
        return self._allocator

    def _require_transaction(self) -> SqlTransaction:
        if self._transaction is None:
            raise self._not_started()
        return self._transaction

    @staticmethod
    def _not_started() -> UnitOfWorkStateError:
        return UnitOfWorkStateError("Transaction SQL non ouverte (utiliser `with`)")


class SqlUnitOfWorkFactory:
    """`UnitOfWorkFactory` SQL : un moteur partagé, un registre de dépôts, des handlers."""

    def __init__(
        self,
        engine: sa.Engine,
        repositories: SqlRepositoryRegistry,
        handlers: Sequence[EventHandler] = (),
    ) -> None:
        self._engine = engine
        self._repositories = tuple(repositories)
        self._handlers = tuple(handlers)

    @property
    def engine(self) -> sa.Engine:
        return self._engine

    def __call__(self, shop_id: ShopId) -> SqlUnitOfWork:
        return SqlUnitOfWork(
            self._engine, shop_id, repositories=self._repositories, handlers=self._handlers
        )
