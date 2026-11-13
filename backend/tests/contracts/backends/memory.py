"""Adaptateur mémoire sous contrat : une `MemoryDatabase` neuve par test."""

from collections.abc import Sequence

from app.application.identity.ports import (
    AdminDelegationDirectory,
    IdentityEventHandler,
    MembershipDirectory,
)
from app.application.plans.ports import EntitlementOverrides
from app.application.ports.event_handler import EventHandler
from app.application.shops.ports import ShopCatalog
from app.domain.shared.ids import ShopId
from app.infrastructure.persistence.memory.alerts import MemoryAlertRepository
from app.infrastructure.persistence.memory.attachments import MEMORY_ATTACHMENT_REPOSITORIES
from app.infrastructure.persistence.memory.imports import MEMORY_IMPORT_REPOSITORIES
from app.infrastructure.persistence.memory.audit_log import MemoryAuditLog
from app.infrastructure.persistence.memory.catalog import MEMORY_CATALOG_REPOSITORIES
from app.infrastructure.persistence.memory.database import MemoryDatabase
from app.infrastructure.persistence.memory.directories import (
    MemoryAdminDelegations,
    MemoryMembershipDirectory,
    MemoryShopCatalog,
)
from app.infrastructure.persistence.memory.entitlements import InMemoryEntitlementOverrides
from app.infrastructure.persistence.memory.expenses import EXPENSE_REPOSITORIES
from app.infrastructure.persistence.memory.identity import MemoryIdentityUnitOfWork
from app.infrastructure.persistence.memory.joined import ShopJoin
from app.infrastructure.persistence.memory.platform_store import MemoryPlatformStore
from app.infrastructure.persistence.memory.purchasing import MEMORY_PURCHASING_REPOSITORIES
from app.infrastructure.persistence.memory.receivables import MEMORY_RECEIVABLES_REPOSITORIES
from app.infrastructure.persistence.memory.reporting import MEMORY_REPORTING_ADAPTERS
from app.infrastructure.persistence.memory.repository import MemoryRepository
from app.infrastructure.persistence.memory.sales import MEMORY_SALES_REPOSITORIES
from app.infrastructure.persistence.memory.sales_returns import (
    MEMORY_SALES_RETURNS_REPOSITORIES,
)
from app.infrastructure.persistence.memory.shops import SHOP_REPOSITORIES
from app.infrastructure.persistence.memory.stock import MEMORY_STOCK_REPOSITORIES
from app.infrastructure.persistence.memory.sync import MEMORY_SYNC_REPOSITORIES
from app.infrastructure.persistence.memory.uow import MemoryUnitOfWork, RepositoryRegistry
from tests.contracts.widget import Widget, WidgetId, WidgetRepository


class MemoryWidgetRepository(MemoryRepository[WidgetId, Widget], WidgetRepository):
    table = "widgets"


REGISTRY: RepositoryRegistry = (
    MemoryWidgetRepository,
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


class MemoryContractBackend:
    def __init__(self) -> None:
        self.database = MemoryDatabase()
        self.store = MemoryPlatformStore()
        self.overrides = InMemoryEntitlementOverrides()

    def uow(self, shop_id: ShopId, handlers: Sequence[EventHandler] = ()) -> MemoryUnitOfWork:
        return MemoryUnitOfWork(self.database, shop_id, repositories=REGISTRY, handlers=handlers)

    def entitlement_overrides(self) -> EntitlementOverrides:
        return self.overrides

    def platform_uow(
        self,
        handlers: Sequence[IdentityEventHandler] = (),
        shop_handlers: Sequence[EventHandler] = (),
    ) -> MemoryIdentityUnitOfWork:
        join = ShopJoin(self.database, REGISTRY, shop_handlers)
        return MemoryIdentityUnitOfWork(self.store, handlers, join)

    def memberships(self) -> MembershipDirectory:
        return MemoryMembershipDirectory(self.database)

    def catalog(self) -> ShopCatalog:
        return MemoryShopCatalog(self.database, self.store)

    def delegations(self) -> AdminDelegationDirectory:
        return MemoryAdminDelegations(self.database)
