"""Événements du stock (T14).

- **Journalisés** (`StockAuditedEvent`, module `stock`) : ajustement (toujours « sensible »,
  AUD-02), lancement, comptage, validation et abandon d'un inventaire.
- **Non journalisés** (`NotAudited`) : variations de la projection, qui ne sont pas des actions
  de l'utilisateur (le document qui les cause est journalisé) ; elles alimentent les alertes :
  `StockTotalChanged` (stock bas, UC-STK-09) et `StockBecameNegative` (RG-T18).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from app.domain.audit.entry import AuditRecord
from app.domain.audit.events import AuditableEvent, NotAudited
from app.domain.audit.values import AuditAction, EntityRef, FieldChange, Performer
from app.domain.catalog.ids import ArticleId
from app.domain.shared.events import DomainEvent
from app.domain.shared.money import Money
from app.domain.shops.ids import LocationId

MODULE = "stock"


@dataclass(frozen=True, kw_only=True)
class StockAuditedEvent(DomainEvent, AuditableEvent):
    """Base abstraite : une sous-classe déclare `action` (et `sensitive` au besoin)."""

    performer: Performer
    entity: EntityRef
    summary: str
    changes: tuple[FieldChange, ...] = ()
    reason: str | None = None

    action: ClassVar[AuditAction]
    sensitive: ClassVar[bool] = False

    def __post_init__(self) -> None:
        if type(self) is StockAuditedEvent or not hasattr(type(self), "action"):
            msg = "StockAuditedEvent est abstraite : déclarer un événement avec son action"
            raise TypeError(msg)
        super().__post_init__()

    def audit_record(self) -> AuditRecord:
        return AuditRecord(
            performer=self.performer,
            action=self.action,
            entity=self.entity,
            module=MODULE,
            summary=self.summary,
            changes=self.changes,
            reason=self.reason,
            sensitive=self.sensitive,
        )


@dataclass(frozen=True, kw_only=True)
class AdjustmentRecorded(StockAuditedEvent):
    """UC-STK-08. `from_inventory` : écart d'un inventaire (l'alerte est celle de l'inventaire)."""

    action = AuditAction.CREATE
    sensitive = True
    from_inventory: bool = False


@dataclass(frozen=True, kw_only=True)
class InventoryStarted(StockAuditedEvent):
    action = AuditAction.CREATE


@dataclass(frozen=True, kw_only=True)
class InventoryCounted(StockAuditedEvent):
    action = AuditAction.UPDATE


@dataclass(frozen=True, kw_only=True)
class InventoryValidated(StockAuditedEvent):
    """Validation : nombre d'écarts et valeur totale au CMP (`None` = non calculable)."""

    action = AuditAction.VALIDATE
    sensitive = True
    gap_count: int
    gap_value: Money | None


@dataclass(frozen=True, kw_only=True)
class InventoryAbandoned(StockAuditedEvent):
    action = AuditAction.CANCEL


@dataclass(frozen=True, kw_only=True)
class StockTotalChanged(DomainEvent, NotAudited):
    """Stock vendable **tous lieux** d'un article avant et après un mouvement (UC-STK-09)."""

    article_id: ArticleId
    article_name: str
    before: Decimal
    after: Decimal
    threshold: Decimal


@dataclass(frozen=True, kw_only=True)
class StockBecameNegative(DomainEvent, NotAudited):
    """Sortie différée acceptée qui rend le stock du lieu négatif (RG-T18, OFF-06)."""

    article_id: ArticleId
    article_name: str
    location_id: LocationId
    location_name: str
    balance: Decimal
