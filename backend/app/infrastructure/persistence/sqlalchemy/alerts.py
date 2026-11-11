"""`AlertRepository` SQL : table `alert`, contrainte `alert_active_dedup` (= `UniqueKey`)."""

from typing import Any

import sqlalchemy as sa

from app.application.alerts.ports import AlertRepository, alert_position
from app.application.ports.pagination import Page, PageRequest, page_of
from app.domain.alerts.alert import Alert, AlertId, AlertType
from app.domain.audit.values import EntityRef
from app.domain.shared.ids import ShopId, UserId
from app.infrastructure.persistence.sqlalchemy.columns import (
    before_cursor,
    from_db,
    from_db_optional,
    to_db,
)
from app.infrastructure.persistence.sqlalchemy.repository import SqlRepository
from app.infrastructure.persistence.sqlalchemy.tables import alert as alert_table


class SqlAlertRepository(SqlRepository[AlertId, Alert], AlertRepository):
    table = alert_table

    def _to_columns(self, aggregate: Alert) -> dict[str, Any]:
        return {
            "recipient_id": aggregate.recipient_id.value,
            "type": aggregate.type.value,
            "entity_type": aggregate.entity.type,
            "entity_id": aggregate.entity.id,
            "entity_number": aggregate.entity.number,
            "message": aggregate.message,
            "read": aggregate.read,
            "created_at": to_db(aggregate.created_at),
            "resolved_at": None if aggregate.resolved_at is None else to_db(aggregate.resolved_at),
            "dedup_key": aggregate.dedup_key,
            "dedup_active_key": aggregate.dedup_active_key,
        }

    def _from_row(self, row: sa.RowMapping) -> Alert:
        return Alert(
            id=AlertId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            recipient_id=UserId(row["recipient_id"]),
            type=AlertType(row["type"]),
            entity=EntityRef(row["entity_type"], row["entity_id"], row["entity_number"]),
            message=row["message"],
            created_at=from_db(row["created_at"]),
            dedup_key=row["dedup_key"],
            read=bool(row["read"]),
            resolved_at=from_db_optional(row["resolved_at"]),
            version=int(row["version"]),
        )

    def _select(self, *conditions: sa.ColumnElement[bool]) -> list[Alert]:
        c = self.table.c
        statement = (
            sa.select(self.table)
            .where(c.shop_id == self.shop_id.value, *conditions)
            .order_by(c.created_at.desc(), c.id.desc())
        )
        rows = self._transaction.fetch_all(statement)
        return self._tracked([self._from_row(row) for row in rows])

    def for_recipient(
        self, recipient_id: UserId, page: PageRequest, *, unread_only: bool = False
    ) -> Page[Alert]:
        c = self.table.c
        conditions = [c.recipient_id == recipient_id.value]
        if unread_only:
            conditions.append(c.read.is_(False))
        if page.after is not None:
            conditions.append(before_cursor(c.created_at, c.id, page.after))
        statement = (
            sa.select(self.table)
            .where(c.shop_id == self.shop_id.value, *conditions)
            .order_by(c.created_at.desc(), c.id.desc())
            .limit(page.limit + 1)
        )
        rows = self._transaction.fetch_all(statement)
        found = page_of([self._from_row(row) for row in rows], page, alert_position)
        return Page(self._tracked(found.items), found.next_cursor)

    def unread_count(self, recipient_id: UserId) -> int:
        c = self.table.c
        statement = sa.select(sa.func.count().label("unread")).where(
            c.shop_id == self.shop_id.value,
            c.recipient_id == recipient_id.value,
            c.read.is_(False),
        )
        row = self._transaction.fetch_one(statement)
        return 0 if row is None else int(row["unread"])

    def find_active(self, recipient_id: UserId, dedup_key: str) -> Alert | None:
        c = self.table.c
        found = self._select(c.recipient_id == recipient_id.value, c.dedup_active_key == dedup_key)
        return found[0] if found else None

    def active_with_key(self, dedup_key: str) -> list[Alert]:
        found = self._select(self.table.c.dedup_active_key == dedup_key)
        return sorted(found, key=alert_position)
