"""Événements du socle, tous journalisés (RG-T01, UC-SOC-06 « chaque changement est inscrit »).

Chaque événement porte l'auteur (`Performer`, rôle au moment de l'action), l'élément visé, un
résumé et les changements avant/après ; la classe fixe l'action, le module et la pastille
« sensible » (changement de droits). `audit_record()` est donc commun à tous.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar

from app.domain.audit.entry import AuditRecord
from app.domain.audit.events import AuditableEvent
from app.domain.audit.values import AuditAction, EntityRef, FieldChange, Performer, Scalar
from app.domain.shared.events import DomainEvent


def diff(before: Mapping[str, Scalar], after: Mapping[str, Scalar]) -> tuple[FieldChange, ...]:
    """Changements champ par champ (ordre de `after`) ; les champs identiques sont omis."""
    if set(before) != set(after):
        msg = f"Comparaison de champs différents : {sorted(set(before) ^ set(after))}"
        raise ValueError(msg)
    return tuple(
        FieldChange(name, before[name], value)
        for name, value in after.items()
        if before[name] != value
    )


@dataclass(frozen=True, kw_only=True)
class ShopAuditedEvent(DomainEvent, AuditableEvent):
    """Base abstraite : une sous-classe déclare `action`, `module` et `sensitive`."""

    performer: Performer
    entity: EntityRef
    summary: str
    changes: tuple[FieldChange, ...] = ()

    action: ClassVar[AuditAction]
    module: ClassVar[str] = "shop"
    sensitive: ClassVar[bool] = False

    def __post_init__(self) -> None:
        if type(self) is ShopAuditedEvent or not hasattr(type(self), "action"):
            msg = "ShopAuditedEvent est abstraite : déclarer un événement avec son action"
            raise TypeError(msg)
        super().__post_init__()

    def audit_record(self) -> AuditRecord:
        return AuditRecord(
            performer=self.performer,
            action=self.action,
            entity=self.entity,
            module=self.module,
            summary=self.summary,
            changes=self.changes,
            sensitive=self.sensitive,
        )


@dataclass(frozen=True, kw_only=True)
class ShopOpened(ShopAuditedEvent):
    action = AuditAction.CREATE
    module = "platform"


@dataclass(frozen=True, kw_only=True)
class ShopAdministered(ShopAuditedEvent):
    """Modules ou statut changés par l'administrateur plateforme (UC-SOC-01, TR-23)."""

    action = AuditAction.CONFIGURE
    module = "platform"
    sensitive = True


@dataclass(frozen=True, kw_only=True)
class SettingsChanged(ShopAuditedEvent):
    action = AuditAction.CONFIGURE


@dataclass(frozen=True, kw_only=True)
class LocationCreated(ShopAuditedEvent):
    action = AuditAction.CREATE


@dataclass(frozen=True, kw_only=True)
class LocationChanged(ShopAuditedEvent):
    action = AuditAction.UPDATE


@dataclass(frozen=True, kw_only=True)
class PaymentModeCreated(ShopAuditedEvent):
    action = AuditAction.CONFIGURE


@dataclass(frozen=True, kw_only=True)
class PaymentModeChanged(ShopAuditedEvent):
    action = AuditAction.CONFIGURE


@dataclass(frozen=True, kw_only=True)
class MemberAdded(ShopAuditedEvent):
    action = AuditAction.CREATE
    module = "members"
    sensitive = True


@dataclass(frozen=True, kw_only=True)
class MemberChanged(ShopAuditedEvent):
    """Rôle, lieu habituel, désactivation ou réactivation (UC-SOC-04)."""

    action = AuditAction.UPDATE
    module = "members"
    sensitive = True


@dataclass(frozen=True, kw_only=True)
class AdminAccessGranted(ShopAuditedEvent):
    action = AuditAction.CONFIGURE
    sensitive = True


@dataclass(frozen=True, kw_only=True)
class AdminAccessRevoked(ShopAuditedEvent):
    action = AuditAction.CONFIGURE
    sensitive = True
