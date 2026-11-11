"""Événements et entrées de journal de démonstration — **tests uniquement**."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.application.audit.ports import AuditLog
from app.application.ports.uow import UnitOfWork
from app.domain.audit.entry import AuditEntry, AuditRecord
from app.domain.audit.events import AuditableEvent, NotAudited
from app.domain.audit.values import AuditAction, EntityRef, FieldChange, Performer
from app.domain.shared.events import DomainEvent
from app.domain.shared.ids import DeviceId, ShopId, UserId
from tests.contracts.widget import NOW, Widget, WidgetId

AUTHOR = UserId.new()
DEVICE = DeviceId.new()


@dataclass(frozen=True, kw_only=True)
class WidgetAudited(DomainEvent, AuditableEvent):
    widget_id: WidgetId
    label: str

    def audit_record(self) -> AuditRecord:
        return AuditRecord(
            performer=Performer(AUTHOR, "owner", DEVICE),
            action=AuditAction.UPDATE,
            entity=EntityRef("widget", self.widget_id.value, "W-1"),
            module="widgets",
            summary=f"Widget renommé en {self.label}",
            changes=(FieldChange("label", "avant", self.label),),
            reason="test",
        )


@dataclass(frozen=True, kw_only=True)
class WidgetIgnored(DomainEvent, NotAudited):
    widget_id: WidgetId


@dataclass(frozen=True, kw_only=True)
class WidgetBroken(DomainEvent, AuditableEvent):
    """Sa traduction échoue : la transaction de l'action doit être annulée."""

    def audit_record(self) -> AuditRecord:
        msg = "traduction impossible"
        raise ValueError(msg)


def widget_with(shop_id: ShopId, *events: type[DomainEvent]) -> Widget:
    """Widget neuf dont les événements en attente sont exactement `events` (dans l'ordre)."""
    widget = Widget.create(shop_id, "w")
    widget.events.pull()  # WidgetCreated n'est pas journalisable
    for kind in events:
        if kind is WidgetAudited:
            widget.events.record(
                WidgetAudited(shop_id=shop_id, occurred_at=NOW, widget_id=widget.id, label="w")
            )
        elif kind is WidgetIgnored:
            widget.events.record(
                WidgetIgnored(shop_id=shop_id, occurred_at=NOW, widget_id=widget.id)
            )
        else:
            widget.events.record(kind(shop_id=shop_id, occurred_at=NOW))
    return widget


def entry(
    shop_id: ShopId,
    *,
    at: datetime = NOW,
    user: UserId = AUTHOR,
    action: AuditAction = AuditAction.CREATE,
    module: str = "sales",
    entity: EntityRef | None = None,
) -> AuditEntry:
    record = AuditRecord(
        performer=Performer(user, "seller", DEVICE),
        action=action,
        entity=entity or EntityRef("sale", None, "V-000124"),
        module=module,
        summary="Vente V-000124 : 1 moto, 780 000 FCFA",
        changes=(FieldChange("price", 780_000, 760_000), FieldChange("note", None, "é")),
    )
    return AuditEntry.inscribe(shop_id, record, received_at=at, default_captured_at=at)


def append_all(uow: UnitOfWork, *entries: AuditEntry) -> None:
    log = AuditLog.within(uow)
    for item in entries:
        log.append(item)


def minutes(n: int) -> timedelta:
    return timedelta(minutes=n)
