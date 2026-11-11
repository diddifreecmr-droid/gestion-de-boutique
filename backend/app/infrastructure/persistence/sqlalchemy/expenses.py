"""Dépôts SQL du module Dépenses (T18) : dépenses (avec leurs tags) et tags.

Une dépense occupe une ligne `expense` et ses lignes `expense_tag` : le gabarit
`SqlRepository` écrit la première, ce dépôt réécrit les secondes dans la même transaction
(supprimer une ligne d'association n'efface aucune donnée métier : la liste des tags est
remplacée, l'avant/après est au journal). Les lectures chargent les tags par lot (`hydrate`).
"""

from collections import defaultdict
from collections.abc import Sequence
from typing import Any
from uuid import UUID

import sqlalchemy as sa

from app.application.expenses.ports import ExpenseRepository, TagRepository
from app.domain.expenses.details import Cancellation, Capture, ExpenseDetails
from app.domain.expenses.expense import Expense, ExpenseStatus
from app.domain.expenses.ids import AttachmentId, ExpenseId, TagId
from app.domain.expenses.tag import Tag
from app.domain.shared.doc_number import DocNumber
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.shops.ids import ExpenseCategoryId, LocationId, PaymentModeId
from app.infrastructure.persistence.sqlalchemy import tables_expenses as t
from app.infrastructure.persistence.sqlalchemy.columns import from_db, to_db
from app.infrastructure.persistence.sqlalchemy.shops import SqlListing
from app.infrastructure.persistence.sqlalchemy.transaction import SqlTransaction


def _value(entity: Any) -> UUID | None:
    return None if entity is None else entity.value


def expense_columns(expense: Expense) -> dict[str, Any]:
    details, capture, cancel = expense.details, expense.capture, expense.cancellation
    return {
        "number": str(expense.number),
        "spent_on": details.spent_on,
        "amount": details.amount,
        "category_id": details.category_id.value,
        "payment_mode_id": details.payment_mode_id.value,
        "description": details.description,
        "location_id": _value(details.location_id),
        "beneficiary": details.beneficiary,
        "attachment_id": _value(details.attachment_id),
        "status": expense.status.value,
        "created_by": capture.created_by.value,
        "device_id": capture.device_id.value,
        "captured_at": to_db(capture.captured_at),
        "received_at": to_db(capture.received_at),
        "cancelled_at": None if cancel is None else to_db(cancel.at),
        "cancelled_by": None if cancel is None else cancel.by.value,
        "cancel_reason": None if cancel is None else cancel.reason,
    }


def expense_from_row(row: sa.RowMapping, tag_ids: tuple[TagId, ...]) -> Expense:
    location, attachment = row["location_id"], row["attachment_id"]
    cancellation = None
    if row["status"] == ExpenseStatus.CANCELLED.value:
        cancellation = Cancellation(
            from_db(row["cancelled_at"]), UserId(row["cancelled_by"]), row["cancel_reason"]
        )
    return Expense(
        id=ExpenseId(row["id"]),
        shop_id=ShopId(row["shop_id"]),
        number=DocNumber.parse(row["number"]),
        details=ExpenseDetails(
            spent_on=row["spent_on"],
            amount=int(row["amount"]),
            category_id=ExpenseCategoryId(row["category_id"]),
            payment_mode_id=PaymentModeId(row["payment_mode_id"]),
            tag_ids=tag_ids,
            description=row["description"],
            location_id=None if location is None else LocationId(location),
            beneficiary=row["beneficiary"],
            attachment_id=None if attachment is None else AttachmentId(attachment),
        ),
        capture=Capture(
            UserId(row["created_by"]),
            DeviceId(row["device_id"]),
            from_db(row["captured_at"]),
            from_db(row["received_at"]),
        ),
        cancellation=cancellation,
        version=int(row["version"]),
    )


def hydrate(
    transaction: SqlTransaction, shop_id: ShopId, rows: Sequence[sa.RowMapping]
) -> list[Expense]:
    """Dépenses des lignes `rows`, avec leurs tags lus en une requête."""
    if not rows:
        return []
    c = t.expense_tag.c
    statement = (
        sa.select(c.expense_id, c.tag_id)
        .where(c.shop_id == shop_id.value, c.expense_id.in_([row["id"] for row in rows]))
        .order_by(c.expense_id, c.position)
    )
    tags: dict[UUID, list[TagId]] = defaultdict(list)
    for link in transaction.fetch_all(statement):
        tags[link["expense_id"]].append(TagId(link["tag_id"]))
    return [expense_from_row(row, tuple(tags[row["id"]])) for row in rows]


class SqlExpenseRepository(SqlListing[ExpenseId, Expense], ExpenseRepository):
    table = t.expense

    def _to_columns(self, aggregate: Expense) -> dict[str, Any]:
        return expense_columns(aggregate)

    def _from_row(self, row: sa.RowMapping) -> Expense:
        return hydrate(self._transaction, self.shop_id, [row])[0]

    def _insert(self, aggregate: Expense) -> None:
        super()._insert(aggregate)
        self._write_tags(aggregate)

    def _save(self, aggregate: Expense, *, expected_version: int) -> None:
        super()._save(aggregate, expected_version=expected_version)
        links = t.expense_tag.c
        self._transaction.write(
            sa.delete(t.expense_tag).where(
                links.shop_id == self.shop_id.value, links.expense_id == aggregate.id.value
            )
        )
        self._write_tags(aggregate)

    def _write_tags(self, expense: Expense) -> None:
        rows = [
            {
                "expense_id": expense.id.value,
                "tag_id": tag.value,
                "shop_id": self.shop_id.value,
                "position": index,
            }
            for index, tag in enumerate(expense.details.tag_ids)
        ]
        if rows:
            self._transaction.write(sa.insert(t.expense_tag).values(rows))

    def list_with_tag(self, tag_id: TagId) -> list[Expense]:
        c, links = self.table.c, t.expense_tag.c
        tagged = sa.select(links.expense_id).where(
            links.shop_id == self.shop_id.value, links.tag_id == tag_id.value
        )
        statement = (
            sa.select(self.table)
            .where(c.shop_id == self.shop_id.value, c.id.in_(tagged))
            .order_by(c.received_at, c.id)
        )
        found = hydrate(self._transaction, self.shop_id, self._transaction.fetch_all(statement))
        for expense in found:
            self._tracker.track(expense, saved=False)
        return found


class SqlTagRepository(SqlListing[TagId, Tag], TagRepository):
    table = t.tag

    def _to_columns(self, aggregate: Tag) -> dict[str, Any]:
        return {
            "name": aggregate.name,
            "name_key": aggregate.name_key,
            "merged_into": _value(aggregate.merged_into),
        }

    def _from_row(self, row: sa.RowMapping) -> Tag:
        merged = row["merged_into"]
        return Tag(
            id=TagId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            name=row["name"],
            merged_into=None if merged is None else TagId(merged),
            version=int(row["version"]),
        )

    def find_by_key(self, key: str) -> Tag | None:
        c = self.table.c
        found = self._select_all(c.id, where=c.name_key == key)
        return found[0] if found else None

    def list_all(self) -> list[Tag]:
        c = self.table.c
        return self._select_all(c.name_key, c.id)


SQL_EXPENSE_REPOSITORIES = (SqlExpenseRepository, SqlTagRepository)
