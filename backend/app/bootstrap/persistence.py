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
from app.infrastructure.persistence.memory.audit_log import MemoryAuditLog
from app.infrastructure.persistence.memory.database import MemoryDatabase
from app.infrastructure.persistence.memory.shops import SHOP_REPOSITORIES
from app.infrastructure.persistence.memory.uow import MemoryUnitOfWorkFactory, RepositoryRegistry
from app.infrastructure.persistence.sqlalchemy.alerts import SqlAlertRepository
from app.infrastructure.persistence.sqlalchemy.audit_log import SqlAuditLog
from app.infrastructure.persistence.sqlalchemy.engine import create_sql_engine
from app.infrastructure.persistence.sqlalchemy.shops_members import SQL_SHOP_REPOSITORIES
from app.infrastructure.persistence.sqlalchemy.uow import (
    SqlRepositoryRegistry,
    SqlUnitOfWorkFactory,
)

MEMORY_REPOSITORIES: RepositoryRegistry = (
    MemoryAuditLog,
    MemoryAlertRepository,
    *SHOP_REPOSITORIES,
)
SQL_REPOSITORIES: SqlRepositoryRegistry = (SqlAuditLog, SqlAlertRepository, *SQL_SHOP_REPOSITORIES)


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
