"""`AuditLog` SQL : table `audit_entry`, **`INSERT` et `SELECT` seulement** (RG-J01).

Aucune instruction `UPDATE` ni `DELETE` n'existe dans ce module. Défense en profondeur prévue
par specs § 8.4 : le rôle de base de l'API n'aura pas ces droits sur `audit_entry` (mesure de
déploiement, T25).
"""

from typing import Any

import sqlalchemy as sa

from app.application.audit.ports import AuditLog, AuditQuery, position
from app.application.ports.pagination import Page, PageRequest, page_of
from app.domain.audit.entry import AuditEntry, AuditEntryId
from app.domain.audit.values import AuditAction, EntityRef, FieldChange, Performer
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.infrastructure.persistence.errors import PRIMARY_KEY, duplicate
from app.infrastructure.persistence.sqlalchemy.columns import before_cursor, from_db, to_db
from app.infrastructure.persistence.sqlalchemy.shop_store import SqlShopStore
from app.infrastructure.persistence.sqlalchemy.tables import audit_entry


def _columns(entry: AuditEntry) -> dict[str, Any]:
    device = entry.performer.device_id
    return {
        "id": entry.id.value,
        "shop_id": entry.shop_id.value,
        "actor_id": entry.performer.user_id.value,
        "role": entry.performer.role,
        "device_id": None if device is None else device.value,
        "action": entry.action.value,
        "module": entry.module,
        "entity_type": entry.entity.type,
        "entity_id": entry.entity.id,
        "entity_number": entry.entity.number,
        "summary": entry.summary,
        "changes": [
            {"field": c.field, "before": c.before, "after": c.after} for c in entry.changes
        ],
        "reason": entry.reason,
        "sensitive": entry.sensitive,
        "captured_at": to_db(entry.captured_at),
        "received_at": to_db(entry.received_at),
    }


def _entry(row: sa.RowMapping) -> AuditEntry:
    device = row["device_id"]
    return AuditEntry(
        id=AuditEntryId(row["id"]),
        shop_id=ShopId(row["shop_id"]),
        performer=Performer(
            UserId(row["actor_id"]), row["role"], None if device is None else DeviceId(device)
        ),
        action=AuditAction(row["action"]),
        entity=EntityRef(row["entity_type"], row["entity_id"], row["entity_number"]),
        module=row["module"],
        summary=row["summary"],
        changes=tuple(FieldChange(c["field"], c["before"], c["after"]) for c in row["changes"]),
        reason=row["reason"],
        sensitive=bool(row["sensitive"]),
        captured_at=from_db(row["captured_at"]),
        received_at=from_db(row["received_at"]),
    )


class SqlAuditLog(SqlShopStore, AuditLog):
    table = audit_entry

    def _append(self, entry: AuditEntry) -> None:
        try:
            self._transaction.write(sa.insert(self.table).values(_columns(entry)))
        except sa.exc.IntegrityError as exc:
            taken = sa.select(self.table.c.id).where(self.table.c.id == entry.id.value)
            if not self._transaction.exists(taken):
                raise  # contrainte imprévue : l'erreur remonte telle quelle (fail-fast)
            raise duplicate(self.table.name, PRIMARY_KEY) from exc

    def search(self, query: AuditQuery, page: PageRequest) -> Page[AuditEntry]:
        c = self.table.c
        conditions: list[sa.ColumnElement[bool]] = [self._own_shop()]
        if query.since is not None:
            conditions.append(c.captured_at >= to_db(query.since))
        if query.until is not None:
            conditions.append(c.captured_at < to_db(query.until))
        if query.user_id is not None:
            conditions.append(c.actor_id == query.user_id.value)
        if query.actions:
            conditions.append(c.action.in_(sorted(a.value for a in query.actions)))
        if query.modules:
            conditions.append(c.module.in_(sorted(query.modules)))
        if query.entity_type is not None:
            conditions.append(c.entity_type == query.entity_type)
        if query.entity_id is not None:
            conditions.append(c.entity_id == query.entity_id)
        if page.after is not None:
            conditions.append(before_cursor(c.received_at, c.id, page.after))
        statement = (
            sa.select(self.table)
            .where(*conditions)
            .order_by(c.received_at.desc(), c.id.desc())
            .limit(page.limit + 1)
        )
        rows = self._transaction.fetch_all(statement)
        return page_of([_entry(row) for row in rows], page, position)
