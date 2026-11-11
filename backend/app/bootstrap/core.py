"""Noyau assemblé une fois par application : stockages, unités de travail, lectures plateforme.

Identité, journal et boutiques partagent **les mêmes** stockages (une base mémoire, ou un
moteur SQL) : c'est ce qui permet la transaction commune plateforme + boutique (T10). Les
handlers de boutique (journal puis alertes) sont posés sur les unités de boutique **et** sur
les unités jointes ; le handler du journal de l'identité, sur l'unité plateforme.

Les règles d'alerte des modules sont branchées **ici, une fois** par répartiteur (stock T14,
ventes T16) :
assembler un module plusieurs fois (outils, tests) ne double jamais une alerte.
"""

from dataclasses import dataclass
from typing import assert_never

from app.application.alerts.dispatcher import AlertDispatcher
from app.application.audit.identity_recorder import IdentityAuditRecorder
from app.application.audit.recorder import AuditRecorder
from app.application.identity.ports import AdminDelegationDirectory, MembershipDirectory
from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.plans.ports import EntitlementOverrides
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.sales.alerts import register_sales_alerts
from app.application.shops.ports import ShopCatalog
from app.application.stock.alerts import register_stock_alerts
from app.bootstrap.config import PersistenceBackend, Settings
from app.bootstrap.persistence import MEMORY_REPOSITORIES, SQL_REPOSITORIES, sql_engine
from app.infrastructure.persistence.memory.database import MemoryDatabase
from app.infrastructure.persistence.memory.directories import (
    MemoryAdminDelegations,
    MemoryMembershipDirectory,
    MemoryShopCatalog,
)
from app.infrastructure.persistence.memory.entitlements import InMemoryEntitlementOverrides
from app.infrastructure.persistence.memory.identity import MemoryIdentityUnitOfWorkFactory
from app.infrastructure.persistence.memory.joined import ShopJoin
from app.infrastructure.persistence.memory.platform_store import MemoryPlatformStore
from app.infrastructure.persistence.memory.uow import MemoryUnitOfWorkFactory
from app.infrastructure.persistence.sqlalchemy.directories import (
    SqlAdminDelegations,
    SqlMembershipDirectory,
    SqlShopCatalog,
)
from app.infrastructure.persistence.sqlalchemy.entitlements import SqlEntitlementOverrides
from app.infrastructure.persistence.sqlalchemy.platform_uow import (
    SqlIdentityUnitOfWorkFactory,
    SqlShopJoin,
)
from app.infrastructure.persistence.sqlalchemy.uow import SqlUnitOfWorkFactory


@dataclass(frozen=True, slots=True, kw_only=True)
class Core:
    clock: Clock
    alerts: AlertDispatcher
    shop_uow_factory: UnitOfWorkFactory
    platform_uow_factory: IdentityUnitOfWorkFactory
    memberships: MembershipDirectory
    catalog: ShopCatalog
    delegations: AdminDelegationDirectory
    overrides: EntitlementOverrides
    database: MemoryDatabase | None = None
    """Base mémoire (adaptateur `memory`), exposée aux outils de démonstration et aux tests."""


def build_core(settings: Settings, clock: Clock) -> Core:
    alerts = AlertDispatcher(clock)
    register_stock_alerts(alerts)
    register_sales_alerts(alerts)
    handlers = (AuditRecorder(clock), alerts)
    backend = settings.persistence_backend
    if backend is PersistenceBackend.MEMORY:
        database, store = MemoryDatabase(), MemoryPlatformStore()
        memberships = MemoryMembershipDirectory(database)
        return Core(
            clock=clock,
            alerts=alerts,
            shop_uow_factory=MemoryUnitOfWorkFactory(database, MEMORY_REPOSITORIES, handlers),
            platform_uow_factory=MemoryIdentityUnitOfWorkFactory(
                store,
                [IdentityAuditRecorder(memberships, clock)],
                ShopJoin(database, MEMORY_REPOSITORIES, handlers),
            ),
            memberships=memberships,
            catalog=MemoryShopCatalog(database, store),
            delegations=MemoryAdminDelegations(database),
            overrides=InMemoryEntitlementOverrides(),
            database=database,
        )
    if backend is PersistenceBackend.POSTGRES:
        engine = sql_engine(settings)
        sql_memberships = SqlMembershipDirectory(engine)
        return Core(
            clock=clock,
            alerts=alerts,
            shop_uow_factory=SqlUnitOfWorkFactory(engine, SQL_REPOSITORIES, handlers),
            platform_uow_factory=SqlIdentityUnitOfWorkFactory(
                engine,
                [IdentityAuditRecorder(sql_memberships, clock)],
                SqlShopJoin(SQL_REPOSITORIES, handlers),
            ),
            memberships=sql_memberships,
            catalog=SqlShopCatalog(engine),
            delegations=SqlAdminDelegations(engine),
            overrides=SqlEntitlementOverrides(engine),
        )
    assert_never(backend)
