"""Choix de l'adaptateur de persistance (specs § 4.1, règle 5).

Changer de base = changer `PERSISTENCE_BACKEND` (et fournir l'adaptateur) : rien d'autre ne
connaît la base. Les registres de dépôts s'allongent avec les modules métier (T10+) ; chaque
port doit y avoir son adaptateur **dans les deux** registres (prouvé par `tests/contracts`).
"""

from collections.abc import Sequence
from typing import assert_never

import sqlalchemy as sa

from app.application.ports.event_handler import EventHandler
from app.application.ports.uow import UnitOfWorkFactory
from app.bootstrap.config import PersistenceBackend, Settings
from app.infrastructure.persistence.memory.alerts import MemoryAlertRepository
from app.infrastructure.persistence.memory.attachments import MEMORY_ATTACHMENT_REPOSITORIES
from app.infrastructure.persistence.memory.audit_log import MemoryAuditLog
from app.infrastructure.persistence.memory.catalog import MEMORY_CATALOG_REPOSITORIES
from app.infrastructure.persistence.memory.database import MemoryDatabase
from app.infrastructure.persistence.memory.expenses import EXPENSE_REPOSITORIES
from app.infrastructure.persistence.memory.imports import MEMORY_IMPORT_REPOSITORIES
from app.infrastructure.persistence.memory.purchasing import MEMORY_PURCHASING_REPOSITORIES
from app.infrastructure.persistence.memory.receivables import MEMORY_RECEIVABLES_REPOSITORIES
from app.infrastructure.persistence.memory.reporting import MEMORY_REPORTING_ADAPTERS
from app.infrastructure.persistence.memory.sales import MEMORY_SALES_REPOSITORIES
from app.infrastructure.persistence.memory.sales_returns import (
    MEMORY_SALES_RETURNS_REPOSITORIES,
)
from app.infrastructure.persistence.memory.shops import SHOP_REPOSITORIES
from app.infrastructure.persistence.memory.stock import MEMORY_STOCK_REPOSITORIES
from app.infrastructure.persistence.memory.sync import MEMORY_SYNC_REPOSITORIES
from app.infrastructure.persistence.memory.uow import MemoryUnitOfWorkFactory, RepositoryRegistry
from app.infrastructure.persistence.sqlalchemy.alerts import SqlAlertRepository
from app.infrastructure.persistence.sqlalchemy.attachments import SQL_ATTACHMENT_REPOSITORIES
from app.infrastructure.persistence.sqlalchemy.audit_log import SqlAuditLog
from app.infrastructure.persistence.sqlalchemy.catalog import SQL_CATALOG_REPOSITORIES
from app.infrastructure.persistence.sqlalchemy.engine import create_sql_engine
from app.infrastructure.persistence.sqlalchemy.expense_query import SQL_EXPENSE_ADAPTERS
from app.infrastructure.persistence.sqlalchemy.imports import SQL_IMPORT_REPOSITORIES
from app.infrastructure.persistence.sqlalchemy.purchasing import SQL_PURCHASING_REPOSITORIES
from app.infrastructure.persistence.sqlalchemy.receivables import SQL_RECEIVABLES_REPOSITORIES
from app.infrastructure.persistence.sqlalchemy.reporting import SQL_REPORTING_ADAPTERS
from app.infrastructure.persistence.sqlalchemy.sales_repository import SQL_SALES_REPOSITORIES
from app.infrastructure.persistence.sqlalchemy.sales_returns import (
    SQL_SALES_RETURNS_REPOSITORIES,
)
from app.infrastructure.persistence.sqlalchemy.shops_members import SQL_SHOP_REPOSITORIES
from app.infrastructure.persistence.sqlalchemy.stock_documents import SQL_STOCK_REPOSITORIES
from app.infrastructure.persistence.sqlalchemy.sync import SQL_SYNC_REPOSITORIES
from app.infrastructure.persistence.sqlalchemy.uow import (
    SqlRepositoryRegistry,
    SqlUnitOfWorkFactory,
)

MEMORY_REPOSITORIES: RepositoryRegistry = (
    MemoryAuditLog,
    MemoryAlertRepository,
    *SHOP_REPOSITORIES,
    *MEMORY_CATALOG_REPOSITORIES,
    *EXPENSE_REPOSITORIES,
    *MEMORY_STOCK_REPOSITORIES,
    *MEMORY_PURCHASING_REPOSITORIES,
    *MEMORY_RECEIVABLES_REPOSITORIES,
    *MEMORY_SALES_REPOSITORIES,
    *MEMORY_SALES_RETURNS_REPOSITORIES,
    *MEMORY_REPORTING_ADAPTERS,
    *MEMORY_SYNC_REPOSITORIES,
    *MEMORY_ATTACHMENT_REPOSITORIES,
    *MEMORY_IMPORT_REPOSITORIES,
)
SQL_REPOSITORIES: SqlRepositoryRegistry = (
    SqlAuditLog,
    SqlAlertRepository,
    *SQL_SHOP_REPOSITORIES,
    *SQL_CATALOG_REPOSITORIES,
    *SQL_EXPENSE_ADAPTERS,
    *SQL_STOCK_REPOSITORIES,
    *SQL_PURCHASING_REPOSITORIES,
    *SQL_RECEIVABLES_REPOSITORIES,
    *SQL_SALES_REPOSITORIES,
    *SQL_SALES_RETURNS_REPOSITORIES,
    *SQL_REPORTING_ADAPTERS,
    *SQL_SYNC_REPOSITORIES,
    *SQL_ATTACHMENT_REPOSITORIES,
    *SQL_IMPORT_REPOSITORIES,
)


def build_unit_of_work_factory(
    settings: Settings, handlers: Sequence[EventHandler] = ()
) -> UnitOfWorkFactory:
    """Fabrique d'unités de travail de l'adaptateur configuré (aucune connexion ouverte ici)."""
    backend = settings.persistence_backend
    if backend is PersistenceBackend.MEMORY:
        return MemoryUnitOfWorkFactory(MemoryDatabase(), MEMORY_REPOSITORIES, handlers)
    if backend is PersistenceBackend.POSTGRES:
        return SqlUnitOfWorkFactory(sql_engine(settings), SQL_REPOSITORIES, handlers)
    assert_never(backend)  # mypy : toute nouvelle valeur de PersistenceBackend doit être câblée


def sql_engine(settings: Settings) -> sa.Engine:
    """Moteur paresseux de `DATABASE_URL` (aucune connexion ouverte ici)."""
    if settings.DATABASE_URL is None:  # déjà refusé par Settings : garde-fou
        msg = "DATABASE_URL manquant pour PERSISTENCE_BACKEND=postgres"
        raise RuntimeError(msg)
    return create_sql_engine(settings.DATABASE_URL.get_secret_value())
