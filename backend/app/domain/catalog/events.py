"""Événements du catalogue, tous journalisés (RG-T01, UC-STK-02 « ancienne et nouvelle valeur »).

Comme pour le socle (`domain/shops/events.py`), chaque événement porte l'auteur, l'article, un
résumé, les changements avant/après et, s'il a été donné, le **motif** ; la classe fixe
l'action et la pastille « sensible » (toute modification de prix l'est, `entry.py`).
"""

from dataclasses import dataclass
from typing import ClassVar

from app.domain.audit.entry import AuditRecord
from app.domain.audit.events import AuditableEvent
from app.domain.audit.values import AuditAction, EntityRef, FieldChange, Performer
from app.domain.shared.events import DomainEvent

MODULE = "catalog"


@dataclass(frozen=True, kw_only=True)
class CatalogEvent(DomainEvent, AuditableEvent):
    """Base abstraite : une sous-classe déclare `action` (et `sensitive` au besoin)."""

    performer: Performer
    entity: EntityRef
    summary: str
    changes: tuple[FieldChange, ...] = ()
    reason: str | None = None

    action: ClassVar[AuditAction]
    sensitive: ClassVar[bool] = False

    def __post_init__(self) -> None:
        if type(self) is CatalogEvent or not hasattr(type(self), "action"):
            msg = "CatalogEvent est abstraite : déclarer un événement avec son action"
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
class ArticleCreated(CatalogEvent):
    action = AuditAction.CREATE


@dataclass(frozen=True, kw_only=True)
class ArticleChanged(CatalogEvent):
    """Détails modifiés (UC-STK-02) : le nom change sans réécrire l'historique."""

    action = AuditAction.UPDATE


@dataclass(frozen=True, kw_only=True)
class ArticlePricesSet(CatalogEvent):
    """Prix de base ou minimum fixés (UC-STK-03) : toujours signalé comme sensible."""

    action = AuditAction.UPDATE
    sensitive = True


@dataclass(frozen=True, kw_only=True)
class ArticleArchived(CatalogEvent):
    action = AuditAction.UPDATE


@dataclass(frozen=True, kw_only=True)
class ArticleReactivated(CatalogEvent):
    action = AuditAction.UPDATE
