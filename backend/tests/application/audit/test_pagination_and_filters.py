"""Curseur opaque, bornes de `limit`, filtres du journal (UC-JRN-01)."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.application.alerts.dispatcher import AlertDispatcher
from app.application.audit.ports import AuditQuery
from app.application.audit.use_cases.consult import JournalFilters
from app.application.ports.pagination import MAX_LIMIT, Cursor, PageRequest
from app.domain.audit.values import AuditAction
from app.domain.shared.errors import ValidationFailed
from app.infrastructure.persistence.memory.clock import FixedClock
from app.infrastructure.persistence.sqlalchemy.columns import from_db, from_db_optional

AT = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def test_cursor_round_trip_and_garbage() -> None:
    cursor = Cursor(AT, uuid4())
    assert Cursor.decode(cursor.encode()) == cursor
    for garbage in ("%%%", "YWJj", ""):
        with pytest.raises(ValidationFailed, match="Curseur"):
            Cursor.decode(garbage)
    with pytest.raises(TypeError):
        Cursor(AT, "id")  # type: ignore[arg-type]


def test_limit_bounds() -> None:
    assert PageRequest.parse(None, None).limit == 50
    for bad in (0, MAX_LIMIT + 1):
        with pytest.raises(ValidationFailed):
            PageRequest(bad)
    with pytest.raises(TypeError):
        PageRequest(True)


def test_period_filter_uses_douala_days() -> None:
    query = JournalFilters(first_day=date(2026, 11, 10)).to_query()
    assert (query.since, query.until) == (
        datetime(2026, 11, 9, 23, 0, tzinfo=UTC),
        datetime(2026, 11, 10, 23, 0, tzinfo=UTC),
    )
    assert JournalFilters().to_query().since is None
    with pytest.raises(ValueError, match="snake_case"):
        JournalFilters(modules={"Ventes"}).to_query()


def test_query_validation() -> None:
    with pytest.raises(ValueError, match="type"):
        AuditQuery(entity_id=uuid4())
    assert AuditQuery(since=AT, actions={AuditAction.LOGIN}).actions == frozenset(
        {AuditAction.LOGIN}
    )


def test_sqlite_naive_instants_are_utc() -> None:
    assert from_db(datetime(2026, 11, 10, 12, 0)) == AT
    assert from_db_optional(None) is None
    with pytest.raises(TypeError):
        from_db("2026-11-10")


def test_unknown_alert_directive_is_refused() -> None:
    with pytest.raises(TypeError, match="Directive"):
        AlertDispatcher(FixedClock(AT))._apply("x", None)  # type: ignore[arg-type]
