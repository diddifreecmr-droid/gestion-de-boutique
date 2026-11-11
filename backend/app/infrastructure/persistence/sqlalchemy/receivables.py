"""Adaptateur SQL du module Créances (T17).

La créance suit le gabarit `SqlRepository` (verrou optimiste sur la ligne `receivable`), puis
ses versements, rappels et garants sont réécrits dans la même transaction
(`receivables_rows.py`). Les recherches par versement, rappel ou rappel dû passent par les
tables enfants, toujours filtrées sur la boutique.
"""

from datetime import date
from typing import Any
from uuid import UUID

import sqlalchemy as sa

from app.application.receivables.ports import ReceivableRepository
from app.domain.catalog.ids import AttachmentId
from app.domain.receivables.follow_up import ReminderStatus
from app.domain.receivables.ids import InstallmentId, ReceivableId, ReminderId
from app.domain.receivables.receivable import Receivable
from app.domain.receivables.values import (
    ReceivableOrigin,
    ReceivableStatus,
    SaleCancellation,
    WriteOff,
)
from app.domain.sales.ids import CustomerId, SaleId
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money
from app.infrastructure.persistence.sqlalchemy import tables_receivables as t
from app.infrastructure.persistence.sqlalchemy.columns import from_db, to_db
from app.infrastructure.persistence.sqlalchemy.receivables_rows import (
    read_children,
    write_children,
)
from app.infrastructure.persistence.sqlalchemy.shops import SqlListing


def _optional(value: Any, kind: Any) -> Any:
    return None if value is None else kind(value)


class SqlReceivableRepository(SqlListing[ReceivableId, Receivable], ReceivableRepository):
    table = t.receivable

    def _to_columns(self, aggregate: Receivable) -> dict[str, Any]:
        r, off, cancel = aggregate, aggregate.write_off, aggregate.sale_cancellation
        return {
            "customer_id": r.customer_id.value,
            "origin": r.origin.value,
            "sale_id": None if r.sale_id is None else r.sale_id.value,
            "sale_number": r.sale_number,
            "sale_total": None if r.sale_total is None else r.sale_total.amount,
            "paid_at_sale": r.paid_at_sale.amount,
            "description": r.description,
            "initial_amount": r.initial_amount.amount,
            "opened_on": r.opened_on,
            "responsible_seller_id": _optional(r.responsible_seller_id, lambda u: u.value),
            "terms": r.terms,
            "status": r.status.value,
            "attachment_ids": [str(a) for a in r.attachment_ids],
            "written_off_on": None if off is None else off.on,
            "write_off_reason": None if off is None else off.reason,
            "written_off_by": None if off is None else off.by.value,
            "written_off_at": None if off is None else to_db(off.at),
            "sale_cancelled_on": None if cancel is None else cancel.on,
            "sale_cancelled_at": None if cancel is None else to_db(cancel.at),
            "recorded_at": to_db(r.recorded_at),
        }

    def _from_row(self, row: sa.RowMapping) -> Receivable:
        installments, reminders, guarantors = read_children(
            self._transaction, self.shop_id.value, row["id"]
        )
        off_on, cancelled_on = row["written_off_on"], row["sale_cancelled_on"]
        return Receivable(
            id=ReceivableId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            customer_id=CustomerId(row["customer_id"]),
            origin=ReceivableOrigin(row["origin"]),
            opened_on=row["opened_on"],
            initial_amount=Money(int(row["initial_amount"])),
            recorded_at=from_db(row["recorded_at"]),
            sale_id=_optional(row["sale_id"], SaleId),
            sale_number=row["sale_number"],
            sale_total=_optional(row["sale_total"], lambda v: Money(int(v))),
            paid_at_sale=Money(int(row["paid_at_sale"])),
            description=row["description"],
            responsible_seller_id=_optional(row["responsible_seller_id"], UserId),
            terms=row["terms"],
            installments=installments,
            reminders=reminders,
            guarantors=guarantors,
            attachment_ids=tuple(AttachmentId.parse(a) for a in row["attachment_ids"]),
            write_off=None
            if off_on is None
            else WriteOff(
                off_on,
                row["write_off_reason"],
                UserId(row["written_off_by"]),
                from_db(row["written_off_at"]),
            ),
            sale_cancellation=None
            if cancelled_on is None
            else SaleCancellation(cancelled_on, from_db(row["sale_cancelled_at"])),
            version=int(row["version"]),
        )

    def _insert(self, aggregate: Receivable) -> None:
        super()._insert(aggregate)
        write_children(self._transaction, aggregate, replace=False)

    def _save(self, aggregate: Receivable, *, expected_version: int) -> None:
        super()._save(aggregate, expected_version=expected_version)
        write_children(self._transaction, aggregate, replace=True)

    def _ordered(self, where: Any = None) -> list[Receivable]:
        c = self.table.c
        return self._select_all(c.opened_on, c.id, where=where)

    def list_all(self, *, responsible: UserId | None = None) -> list[Receivable]:
        c = self.table.c
        return self._ordered(
            None if responsible is None else c.responsible_seller_id == responsible.value
        )

    def for_customer(
        self, customer_id: CustomerId, *, responsible: UserId | None = None
    ) -> list[Receivable]:
        c = self.table.c
        where = c.customer_id == customer_id.value
        if responsible is not None:
            where = sa.and_(where, c.responsible_seller_id == responsible.value)
        return self._ordered(where)

    def _parent_of(self, child: sa.Table, child_id: UUID) -> Receivable | None:
        statement = sa.select(child.c.receivable_id).where(
            child.c.id == child_id, child.c.shop_id == self.shop_id.value
        )
        row = self._transaction.fetch_one(statement)
        return None if row is None else self.find(ReceivableId(row["receivable_id"]))

    def find_by_installment(self, installment_id: InstallmentId) -> Receivable | None:
        return self._parent_of(t.installment, installment_id.value)

    def find_by_reminder(self, reminder_id: ReminderId) -> Receivable | None:
        return self._parent_of(t.receivable_reminder, reminder_id.value)

    def with_due_reminders(self, today: date) -> list[Receivable]:
        m = t.receivable_reminder.c
        due = (
            sa.select(m.receivable_id)
            .where(
                m.shop_id == self.shop_id.value,
                m.status != ReminderStatus.DONE.value,
                m.remind_on <= today,
                sa.or_(m.alerted_for.is_(None), m.alerted_for != m.remind_on),
            )
            .distinct()
        )
        c = self.table.c
        return self._ordered(sa.and_(c.id.in_(due), c.status != ReceivableStatus.CANCELLED.value))


SQL_RECEIVABLES_REPOSITORIES = (SqlReceivableRepository,)
