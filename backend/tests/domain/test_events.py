"""Événements de domaine et collecteur (base de l'unité de travail T05)."""

from dataclasses import FrozenInstanceError, dataclass
from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.domain.shared.events import DomainEvent, EventCollector
from app.domain.shared.ids import EventId, ShopId, UserId

SHOP = ShopId.new()
NOW = datetime(2026, 11, 11, 9, 30, tzinfo=UTC)


@dataclass(frozen=True, kw_only=True)
class ThingHappened(DomainEvent):
    label: str


def _event(label: str = "a", occurred_at: datetime = NOW) -> ThingHappened:
    return ThingHappened(shop_id=SHOP, occurred_at=occurred_at, label=label)


def test_event_carries_identity_shop_and_utc_instant() -> None:
    event = _event()
    assert isinstance(event.event_id, EventId)
    assert event.shop_id == SHOP
    assert event.occurred_at == NOW
    assert event.label == "a"
    assert _event().event_id != event.event_id


def test_occurred_at_is_normalized_to_utc() -> None:
    local = datetime(2026, 11, 11, 10, 30, tzinfo=timezone(timedelta(hours=1)))
    event = _event(occurred_at=local)
    assert event.occurred_at.tzinfo is UTC
    assert event.occurred_at == NOW


def test_naive_instant_is_refused() -> None:
    with pytest.raises(ValueError, match="naïf"):
        _event(occurred_at=datetime(2026, 11, 11, 9, 30))  # naïf exprès : refus testé


def test_event_is_frozen() -> None:
    event = _event()
    with pytest.raises(FrozenInstanceError):
        event.label = "b"  # type: ignore[misc]  # on prouve justement l'immuabilité


def test_base_event_is_abstract() -> None:
    with pytest.raises(TypeError, match="abstraite"):
        DomainEvent(shop_id=SHOP, occurred_at=NOW)


def test_typed_ids_are_enforced() -> None:
    with pytest.raises(TypeError, match="ShopId"):
        # Refus à l'exécution d'un identifiant du mauvais type, prouvé ici.
        ThingHappened(shop_id=UserId.new(), occurred_at=NOW, label="x")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="EventId"):
        ThingHappened(
            shop_id=SHOP,
            occurred_at=NOW,
            label="x",
            event_id=SHOP,  # type: ignore[arg-type]  # refus à l'exécution prouvé ici
        )


def test_collector_keeps_order_and_pull_empties_it() -> None:
    collector = EventCollector()
    first, second = _event("1"), _event("2")
    collector.record(first)
    collector.record(second)
    assert len(collector) == 2
    assert list(collector) == [first, second]
    assert len(collector) == 2  # l'itération ne retire rien
    assert collector.pull() == (first, second)
    assert len(collector) == 0
    assert collector.pull() == ()


def test_collector_refuses_non_events() -> None:
    with pytest.raises(TypeError, match="DomainEvent"):
        EventCollector().record("pas un événement")  # type: ignore[arg-type]  # prouvé ici
