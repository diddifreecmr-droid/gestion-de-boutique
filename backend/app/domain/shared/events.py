"""Événements de domaine et collecteur (specs § 4.4).

Un agrégat **dépose** ses événements dans son `EventCollector` ; l'unité de travail (T05) les
**retire** (`pull`) après validation de la transaction pour les publier. Ce module ne contient ni
bus ni infrastructure.

Déclarer un événement :

    @dataclass(frozen=True, kw_only=True)
    class SaleCreated(DomainEvent):
        sale_id: SaleId
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.shared.business_day import require_aware
from app.domain.shared.ids import EventId, ShopId


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base abstraite : `shop_id` (isolation), `occurred_at` (ramené en UTC), `event_id`."""

    shop_id: ShopId
    occurred_at: datetime
    event_id: EventId = field(default_factory=EventId.new)

    def __post_init__(self) -> None:
        if type(self) is DomainEvent:
            msg = "DomainEvent est abstraite : déclarer un événement typé"
            raise TypeError(msg)
        if not isinstance(self.shop_id, ShopId):
            msg = f"shop_id doit être un ShopId, reçu {type(self.shop_id).__name__}"
            raise TypeError(msg)
        if not isinstance(self.event_id, EventId):
            msg = f"event_id doit être un EventId, reçu {type(self.event_id).__name__}"
            raise TypeError(msg)
        # Instance gelée : seule voie pour stocker la forme UTC normalisée.
        object.__setattr__(self, "occurred_at", require_aware(self.occurred_at))


class EventCollector:
    """File ordonnée des événements en attente d'un agrégat."""

    __slots__ = ("_pending",)

    def __init__(self) -> None:
        self._pending: list[DomainEvent] = []

    def record(self, event: DomainEvent) -> None:
        if not isinstance(event, DomainEvent):
            msg = f"Seul un DomainEvent peut être enregistré, reçu {type(event).__name__}"
            raise TypeError(msg)
        self._pending.append(event)

    def pull(self) -> tuple[DomainEvent, ...]:
        """Renvoie les événements dans l'ordre de dépôt et vide la file."""
        events = tuple(self._pending)
        self._pending.clear()
        return events

    def __len__(self) -> int:
        return len(self._pending)

    def __iter__(self) -> Iterator[DomainEvent]:
        """Lecture sans retrait (copie : la file ne peut pas changer pendant l'itération)."""
        return iter(tuple(self._pending))
