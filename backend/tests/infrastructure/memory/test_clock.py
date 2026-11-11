"""Horloge contrôlable `FixedClock` et date métier dérivée du port `Clock`."""

from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from app.infrastructure.persistence.memory.clock import FixedClock

INSTANT = datetime(2026, 11, 11, 9, 30, tzinfo=UTC)


def test_now_is_fixed_and_normalized_to_utc() -> None:
    clock = FixedClock(datetime(2026, 11, 11, 10, 30, tzinfo=timezone(timedelta(hours=1))))
    assert clock.now() == INSTANT
    assert clock.now().tzinfo is UTC
    assert clock.now() == clock.now()


def test_advance_and_move_to() -> None:
    clock = FixedClock(INSTANT)
    assert clock.advance(timedelta(hours=2)) == INSTANT + timedelta(hours=2)
    assert clock.now() == INSTANT + timedelta(hours=2)
    clock.move_to(datetime(2027, 1, 1, tzinfo=UTC))
    assert clock.now() == datetime(2027, 1, 1, tzinfo=UTC)


def test_naive_instants_are_refused() -> None:
    with pytest.raises(ValueError, match="naïf"):
        FixedClock(datetime(2026, 11, 11, 9, 30))  # naïf exprès : refus testé
    clock = FixedClock(INSTANT)
    with pytest.raises(ValueError, match="naïf"):
        clock.move_to(datetime(2026, 11, 11, 9, 30))  # naïf exprès : refus testé


def test_advance_requires_a_timedelta() -> None:
    with pytest.raises(TypeError, match="timedelta"):
        FixedClock(INSTANT).advance(3600)  # type: ignore[arg-type]  # refus à l'exécution prouvé


def test_today_is_the_business_date_in_douala() -> None:
    late_evening_utc = datetime(2026, 11, 11, 23, 30, tzinfo=UTC)  # 00 h 30 le 12 à Douala
    assert FixedClock(late_evening_utc).today() == date(2026, 11, 12)
