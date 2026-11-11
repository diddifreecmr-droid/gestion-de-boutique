"""Événement et règle d'alerte de démonstration (stock bas fictif) — **tests uniquement**."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta

from app.application.alerts.dispatcher import AlertDirective, AlertNotice, AlertResolution
from app.application.ports.uow import UnitOfWork
from app.domain.alerts.alert import Alert, AlertType
from app.domain.audit.events import NotAudited
from app.domain.audit.values import EntityRef
from app.domain.shared.events import DomainEvent
from app.domain.shared.ids import ShopId, UserId
from tests.contracts.widget import NOW, Widget

OWNER = UserId.new()
ACCOUNTANT = UserId.new()
ARTICLE = EntityRef("article", UserId.new().value, "HJ125")


@dataclass(frozen=True, kw_only=True)
class StockChanged(DomainEvent, NotAudited):
    level: int


def low_stock_rule(event: StockChanged, uow: UnitOfWork) -> Iterable[AlertDirective]:
    """Seuil 5 : sous le seuil → alerte (une fois) à O et C ; au-dessus → résolution."""
    key = f"low_stock:{ARTICLE.id}"
    if event.level < 5:
        yield AlertNotice(
            recipients=(OWNER, ACCOUNTANT, OWNER),
            type=AlertType.LOW_STOCK,
            entity=ARTICLE,
            message=f"Stock bas : HJ125 ({event.level})",
            dedup_key=key,
        )
    else:
        yield AlertResolution(key)


def stock_event(shop_id: ShopId, level: int) -> Widget:
    """Agrégat porteur d'un `StockChanged` (le widget sert de support d'événements)."""
    widget = Widget.create(shop_id, "support")
    widget.events.pull()
    widget.events.record(StockChanged(shop_id=shop_id, occurred_at=NOW, level=level))
    return widget


def alert_for(
    shop_id: ShopId, recipient: UserId = OWNER, key: str | None = "k", minute: int = 0
) -> Alert:
    return Alert.raise_for(
        shop_id=shop_id,
        recipient_id=recipient,
        type=AlertType.SALE_ERROR_REPORTED,
        entity=ARTICLE,
        message="Erreur signalée sur V-000001",
        now=NOW + timedelta(minutes=minute),
        dedup_key=key,
    )
