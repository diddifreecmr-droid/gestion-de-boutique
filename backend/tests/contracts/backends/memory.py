"""Adaptateur mémoire sous contrat : une `MemoryDatabase` neuve par test."""

from collections.abc import Sequence

from app.application.plans.ports import EntitlementOverrides
from app.application.ports.event_handler import EventHandler
from app.domain.shared.ids import ShopId
from app.infrastructure.persistence.memory.alerts import MemoryAlertRepository
from app.infrastructure.persistence.memory.audit_log import MemoryAuditLog
from app.infrastructure.persistence.memory.database import MemoryDatabase
from app.infrastructure.persistence.memory.entitlements import InMemoryEntitlementOverrides
from app.infrastructure.persistence.memory.repository import MemoryRepository
from app.infrastructure.persistence.memory.uow import MemoryUnitOfWork, RepositoryRegistry
from tests.contracts.widget import Widget, WidgetId, WidgetRepository


class MemoryWidgetRepository(MemoryRepository[WidgetId, Widget], WidgetRepository):
    table = "widgets"


REGISTRY: RepositoryRegistry = (MemoryWidgetRepository, MemoryAuditLog, MemoryAlertRepository)


class MemoryContractBackend:
    def __init__(self) -> None:
        self.database = MemoryDatabase()
        self.overrides = InMemoryEntitlementOverrides()

    def uow(self, shop_id: ShopId, handlers: Sequence[EventHandler] = ()) -> MemoryUnitOfWork:
        return MemoryUnitOfWork(self.database, shop_id, repositories=REGISTRY, handlers=handlers)

    def entitlement_overrides(self) -> EntitlementOverrides:
        return self.overrides
