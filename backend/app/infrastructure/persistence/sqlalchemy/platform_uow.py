"""Unité de travail SQL **plateforme** (identité, comptes commerçants) et unités jointes.

Une seule connexion, une seule transaction de base : les dépôts plateforme et ceux des
unités de boutique jointes (`join_shop`) écrivent **dans la même transaction**, validée ou
annulée d'un bloc par l'unité plateforme (voir `application/identity/uow.py`). Une unité
jointe qui a écrit puis s'annule condamne la transaction : l'unité plateforme refuse ensuite
de valider (`UnitOfWorkStateError`) et tout est annulé.
"""

from collections.abc import Sequence
from dataclasses import dataclass

import sqlalchemy as sa

from app.application.identity.ports import IdentityEventHandler
from app.application.identity.repositories import (
    DeviceSessionRepository,
    MerchantAccountRepository,
    UserRepository,
)
from app.application.identity.uow import IdentityUnitOfWork
from app.application.ports.errors import UnitOfWorkStateError
from app.application.ports.event_handler import EventHandler
from app.application.ports.uow import UnitOfWork
from app.domain.shared.ids import ShopId
from app.infrastructure.persistence.sqlalchemy.identity import (
    SqlDeviceSessionRepository,
    SqlMerchantAccountRepository,
    SqlUserRepository,
)
from app.infrastructure.persistence.sqlalchemy.numbering import SqlDocumentNumberAllocator
from app.infrastructure.persistence.sqlalchemy.transaction import SqlTransaction
from app.infrastructure.persistence.sqlalchemy.uow import SqlRepositoryRegistry, SqlUnitOfWork

_DOOMED = "Une unité de boutique jointe a échoué : la transaction entière est annulée"


@dataclass(frozen=True, slots=True)
class SqlShopJoin:
    repositories: SqlRepositoryRegistry
    handlers: Sequence[EventHandler] = ()


class JoinedSqlUnitOfWork(SqlUnitOfWork):
    """Unité de boutique sur la transaction de son hôte ; son `commit` ne valide rien."""

    def __init__(self, host: "SqlIdentityUnitOfWork", join: SqlShopJoin, shop_id: ShopId) -> None:
        super().__init__(
            host.engine, shop_id, repositories=join.repositories, handlers=join.handlers
        )
        self._host = host
        self._writes_at_begin = 0

    def _begin(self) -> None:
        transaction = self._host.shared_transaction()
        self._transaction = transaction
        self._allocator = SqlDocumentNumberAllocator(transaction, self.shop_id)
        self._writes_at_begin = transaction.write_count

    def _commit(self) -> None:
        """L'hôte validera cette transaction avec la sienne."""

    def _rollback(self) -> None:
        if self._require_transaction().write_count != self._writes_at_begin:
            self._host.doom()

    def _has_pending_changes(self) -> bool:
        return self._require_transaction().write_count != self._writes_at_begin


class SqlIdentityUnitOfWork(IdentityUnitOfWork):
    def __init__(
        self,
        engine: sa.Engine,
        handlers: Sequence[IdentityEventHandler] = (),
        join: SqlShopJoin | None = None,
    ) -> None:
        super().__init__(handlers)
        self.engine = engine
        self._join = join
        self._transaction: SqlTransaction | None = None
        self._doomed = False

    def _begin(self) -> None:
        self._transaction = SqlTransaction(self.engine)

    def _commit(self) -> None:
        if self._doomed:
            raise UnitOfWorkStateError(_DOOMED)
        self.shared_transaction().commit()

    def _rollback(self) -> None:
        self.shared_transaction().discard()

    def _has_pending_changes(self) -> bool:
        return self.shared_transaction().has_changes

    def _users(self) -> UserRepository:
        return SqlUserRepository(self, self.shared_transaction())

    def _sessions(self) -> DeviceSessionRepository:
        return SqlDeviceSessionRepository(self, self.shared_transaction())

    def _merchants(self) -> MerchantAccountRepository:
        return SqlMerchantAccountRepository(self, self.shared_transaction())

    def _join_shop(self, shop_id: ShopId) -> UnitOfWork:
        if self._join is None:
            msg = "Unité plateforme sans SqlShopJoin : impossible de joindre une boutique"
            raise LookupError(msg)
        if self._doomed:
            raise UnitOfWorkStateError(_DOOMED)
        return JoinedSqlUnitOfWork(self, self._join, shop_id)

    def shared_transaction(self) -> SqlTransaction:
        if self._transaction is None:
            msg = "Transaction SQL plateforme non ouverte (utiliser `with`)"
            raise UnitOfWorkStateError(msg)
        return self._transaction

    def doom(self) -> None:
        self._doomed = True


class SqlIdentityUnitOfWorkFactory:
    def __init__(
        self,
        engine: sa.Engine,
        handlers: Sequence[IdentityEventHandler] = (),
        join: SqlShopJoin | None = None,
    ) -> None:
        self._engine = engine
        self._handlers = tuple(handlers)
        self._join = join

    def __call__(self) -> SqlIdentityUnitOfWork:
        return SqlIdentityUnitOfWork(self._engine, self._handlers, self._join)
