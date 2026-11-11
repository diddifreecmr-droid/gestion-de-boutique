"""Agrégat de démonstration `Widget` et son port — **tests uniquement**.

Il n'a aucun sens métier : il exerce la mécanique des ports (identité, boutique, version,
unicité de `code` par boutique, événements). Les vrais agrégats arrivent avec T13+.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.application.ports.aggregate import UniqueKey
from app.application.ports.repository import Repository
from app.domain.shared.events import DomainEvent, EventCollector
from app.domain.shared.ids import EntityId, ShopId

NOW = datetime(2026, 11, 11, 9, 30, tzinfo=UTC)


class WidgetId(EntityId):
    __slots__ = ()


@dataclass(frozen=True, kw_only=True)
class WidgetCreated(DomainEvent):
    widget_id: WidgetId
    label: str


@dataclass(frozen=True, kw_only=True)
class WidgetRenamed(DomainEvent):
    widget_id: WidgetId
    label: str


@dataclass(eq=False)
class Widget:
    id: WidgetId
    shop_id: ShopId
    label: str
    code: str | None = None
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    @classmethod
    def create(cls, shop_id: ShopId, label: str, *, code: str | None = None) -> "Widget":
        widget = cls(WidgetId.new(), shop_id, label, code)
        widget.events.record(
            WidgetCreated(shop_id=shop_id, occurred_at=NOW, widget_id=widget.id, label=label)
        )
        return widget

    def rename(self, label: str) -> None:
        self.label = label
        self.events.record(
            WidgetRenamed(shop_id=self.shop_id, occurred_at=NOW, widget_id=self.id, label=label)
        )


class WidgetRepository(Repository[WidgetId, Widget]):
    """Port de démonstration : `code` est unique dans une boutique (non contraint si `None`)."""

    def unique_keys(self) -> Sequence[UniqueKey[Widget]]:
        return (UniqueKey("widget_code", lambda widget: widget.code),)
