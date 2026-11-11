"""Journée métier Africa/Douala et fenêtre de date RG-T09 (H3, TR-07)."""

from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from app.domain.shared.business_day import (
    BUSINESS_TZ,
    MAX_BACKDATE_DAYS,
    business_date,
    day_bounds_utc,
    period_bounds_utc,
    require_aware,
    validate_entry_date,
)
from app.domain.shared.errors import DateOutOfRange

TODAY = date(2026, 11, 11)


def test_timezone_is_available_and_is_utc_plus_one() -> None:
    assert str(BUSINESS_TZ) == "Africa/Douala"
    assert datetime(2026, 7, 1, tzinfo=BUSINESS_TZ).utcoffset() == timedelta(hours=1)
    assert datetime(2026, 1, 1, tzinfo=BUSINESS_TZ).utcoffset() == timedelta(hours=1)


@pytest.mark.parametrize(
    ("instant", "expected"),
    [
        (datetime(2026, 11, 10, 22, 59, tzinfo=UTC), date(2026, 11, 10)),
        (datetime(2026, 11, 10, 23, 0, tzinfo=UTC), date(2026, 11, 11)),
        (datetime(2026, 11, 11, 22, 59, 59, tzinfo=UTC), date(2026, 11, 11)),
        (datetime(2026, 11, 11, 1, 0, tzinfo=timezone(timedelta(hours=3))), date(2026, 11, 10)),
    ],
)
def test_business_date(instant: datetime, expected: date) -> None:
    assert business_date(instant) == expected


def test_naive_datetimes_are_refused() -> None:
    with pytest.raises(ValueError, match="naïf"):
        business_date(datetime(2026, 11, 11, 12, 0))  # naïf exprès : refus testé
    with pytest.raises(TypeError, match="datetime"):
        require_aware(TODAY)  # type: ignore[arg-type]  # refus à l'exécution prouvé ici


def test_require_aware_converts_to_utc() -> None:
    local = datetime(2026, 11, 11, 8, 0, tzinfo=BUSINESS_TZ)
    assert require_aware(local) == datetime(2026, 11, 11, 7, 0, tzinfo=UTC)
    assert require_aware(local).tzinfo is UTC


def test_day_bounds_are_half_open_in_utc() -> None:
    start, end = day_bounds_utc(TODAY)
    assert start == datetime(2026, 11, 10, 23, 0, tzinfo=UTC)
    assert end == datetime(2026, 11, 11, 23, 0, tzinfo=UTC)
    assert business_date(start) == TODAY
    assert business_date(end - timedelta(microseconds=1)) == TODAY
    assert business_date(end) == TODAY + timedelta(days=1)


def test_period_bounds() -> None:
    start, end = period_bounds_utc(date(2026, 11, 1), date(2026, 11, 30))
    assert start == datetime(2026, 10, 31, 23, 0, tzinfo=UTC)
    assert end == datetime(2026, 11, 30, 23, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="inversée"):
        period_bounds_utc(date(2026, 11, 2), date(2026, 11, 1))


def test_bounds_refuse_datetime_instead_of_date() -> None:
    with pytest.raises(TypeError, match="date"):
        day_bounds_utc(datetime(2026, 11, 11, tzinfo=UTC))


# ---------------------------------------------------------------------------- RG-T09
@pytest.mark.parametrize("is_owner", [True, False])
def test_today_is_always_accepted(is_owner: bool) -> None:
    assert validate_entry_date(TODAY, TODAY, is_owner=is_owner) == TODAY


@pytest.mark.parametrize("is_owner", [True, False])
def test_future_is_refused_for_everyone(is_owner: bool) -> None:
    with pytest.raises(DateOutOfRange, match="futur") as excinfo:
        validate_entry_date(TODAY + timedelta(days=1), TODAY, is_owner=is_owner)
    assert excinfo.value.code == "DATE_OUT_OF_RANGE"
    assert excinfo.value.details["max_date"] == "2026-11-11"


def test_owner_has_unlimited_past() -> None:
    old = date(2019, 1, 1)
    assert validate_entry_date(old, TODAY, is_owner=True) == old


def test_other_roles_go_back_seven_days_at_most() -> None:
    limit = TODAY - timedelta(days=MAX_BACKDATE_DAYS)
    assert MAX_BACKDATE_DAYS == 7
    assert validate_entry_date(limit, TODAY, is_owner=False) == limit
    with pytest.raises(DateOutOfRange, match="7 jours") as excinfo:
        validate_entry_date(limit - timedelta(days=1), TODAY, is_owner=False)
    assert dict(excinfo.value.details) == {
        "entry_date": "2026-11-03",
        "min_date": "2026-11-04",
        "max_date": "2026-11-11",
    }


def test_owner_error_details_have_no_min_date() -> None:
    with pytest.raises(DateOutOfRange) as excinfo:
        validate_entry_date(TODAY + timedelta(days=2), TODAY, is_owner=True)
    assert excinfo.value.details["min_date"] is None


def test_entry_date_must_be_a_plain_date() -> None:
    with pytest.raises(TypeError, match="entry_date"):
        validate_entry_date(datetime(2026, 11, 11, tzinfo=UTC), TODAY, is_owner=True)
    with pytest.raises(TypeError, match="today"):
        validate_entry_date(TODAY, "2026-11-11", is_owner=True)  # type: ignore[arg-type]  # prouvé
