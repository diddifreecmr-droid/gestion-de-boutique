"""Lignes enfants d'une créance (versements, rappels, garants) ↔ objets du domaine (T17).

Lues et réécrites **avec** la créance par `SqlReceivableRepository` ; filtrées sur la boutique,
dans l'ordre d'enregistrement (`position`).
"""

from typing import Any
from uuid import UUID

import sqlalchemy as sa

from app.application.receivables.ports import INSTALLMENT_NUMBER
from app.domain.catalog.ids import AttachmentId
from app.domain.purchasing.values import Cancellation, Capture
from app.domain.receivables.follow_up import Guarantor, Reminder, ReminderStatus
from app.domain.receivables.ids import GuarantorId, InstallmentId, ReminderId
from app.domain.receivables.installment import Installment, InstallmentNature
from app.domain.receivables.receivable import Receivable
from app.domain.sales.customer import IdDocumentType
from app.domain.shared.doc_number import DocNumber
from app.domain.shared.ids import DeviceId, UserId
from app.domain.shared.money import Money
from app.domain.shops.ids import PaymentModeId
from app.infrastructure.persistence.errors import duplicate
from app.infrastructure.persistence.sqlalchemy import tables_receivables as t
from app.infrastructure.persistence.sqlalchemy.columns import from_db, to_db
from app.infrastructure.persistence.sqlalchemy.transaction import SqlTransaction

CHILDREN = (t.installment, t.receivable_reminder, t.guarantor)
Children = tuple[tuple[Installment, ...], tuple[Reminder, ...], tuple[Guarantor, ...]]


def _rows(
    transaction: SqlTransaction, table: sa.Table, shop_id: UUID, receivable_id: UUID
) -> list[sa.RowMapping]:
    statement = (
        sa.select(table)
        .where(table.c.receivable_id == receivable_id, table.c.shop_id == shop_id)
        .order_by(table.c.position)
    )
    return transaction.fetch_all(statement)


def _installment(row: sa.RowMapping) -> Installment:
    cancelled = row["cancelled_at"]
    return Installment(
        id=InstallmentId(row["id"]),
        number=DocNumber.parse(row["number"]),
        paid_on=row["paid_on"],
        amount=Money(int(row["amount"])),
        mode_id=PaymentModeId(row["mode_id"]),
        capture=Capture(
            UserId(row["created_by"]),
            DeviceId(row["device_id"]),
            from_db(row["captured_at"]),
            from_db(row["received_at"]),
        ),
        nature=InstallmentNature(row["nature"]),
        reference=row["reference"],
        cancellation=None
        if cancelled is None
        else Cancellation(from_db(cancelled), UserId(row["cancelled_by"]), row["cancel_reason"]),
        to_refund=bool(row["to_refund"]),
    )


def _reminder(row: sa.RowMapping) -> Reminder:
    return Reminder(
        id=ReminderId(row["id"]),
        remind_on=row["remind_on"],
        created_by=UserId(row["created_by"]),
        created_at=from_db(row["created_at"]),
        note=row["note"],
        status=ReminderStatus(row["status"]),
        alerted_for=row["alerted_for"],
    )


def _guarantor(row: sa.RowMapping) -> Guarantor:
    doc_type, photo = row["id_doc_type"], row["id_doc_photo_id"]
    return Guarantor(
        id=GuarantorId(row["id"]),
        name=row["name"],
        phone=row["phone"],
        added_by=UserId(row["added_by"]),
        added_at=from_db(row["added_at"]),
        relation=row["relation"],
        id_doc_type=None if doc_type is None else IdDocumentType(doc_type),
        id_doc_number=row["id_doc_number"],
        id_doc_photo_id=None if photo is None else AttachmentId(photo),
    )


def read_children(transaction: SqlTransaction, shop_id: UUID, receivable_id: UUID) -> Children:
    def rows(table: sa.Table) -> list[sa.RowMapping]:
        return _rows(transaction, table, shop_id, receivable_id)

    return (
        tuple(_installment(row) for row in rows(t.installment)),
        tuple(_reminder(row) for row in rows(t.receivable_reminder)),
        tuple(_guarantor(row) for row in rows(t.guarantor)),
    )


def _installment_values(item: Installment) -> dict[str, Any]:
    cancel, capture = item.cancellation, item.capture
    return {
        "id": item.id.value,
        "number": str(item.number),
        "paid_on": item.paid_on,
        "amount": item.amount.amount,
        "mode_id": item.mode_id.value,
        "reference": item.reference,
        "nature": item.nature.value,
        "status": item.status.value,
        "to_refund": item.to_refund,
        "created_by": capture.created_by.value,
        "device_id": capture.device_id.value,
        "captured_at": to_db(capture.captured_at),
        "received_at": to_db(capture.received_at),
        "cancelled_at": None if cancel is None else to_db(cancel.at),
        "cancelled_by": None if cancel is None else cancel.by.value,
        "cancel_reason": None if cancel is None else cancel.reason,
    }


def _reminder_values(item: Reminder) -> dict[str, Any]:
    return {
        "id": item.id.value,
        "remind_on": item.remind_on,
        "note": item.note,
        "status": item.status.value,
        "alerted_for": item.alerted_for,
        "created_by": item.created_by.value,
        "created_at": to_db(item.created_at),
    }


def _guarantor_values(item: Guarantor) -> dict[str, Any]:
    photo = item.id_doc_photo_id
    return {
        "id": item.id.value,
        "name": item.name,
        "phone": item.phone,
        "relation": item.relation,
        "id_doc_type": None if item.id_doc_type is None else item.id_doc_type.value,
        "id_doc_number": item.id_doc_number,
        "id_doc_photo_id": None if photo is None else photo.value,
        "added_by": item.added_by.value,
        "added_at": to_db(item.added_at),
    }


def write_children(transaction: SqlTransaction, receivable: Receivable, *, replace: bool) -> None:
    ids = {"receivable_id": receivable.id.value, "shop_id": receivable.shop_id.value}
    if replace:
        for table in CHILDREN:
            transaction.write(
                sa.delete(table).where(
                    table.c.receivable_id == receivable.id.value,
                    table.c.shop_id == receivable.shop_id.value,
                )
            )
    rows: list[tuple[sa.Table, list[dict[str, Any]]]] = [
        (t.installment, [_installment_values(i) for i in receivable.installments]),
        (t.receivable_reminder, [_reminder_values(r) for r in receivable.reminders]),
        (t.guarantor, [_guarantor_values(g) for g in receivable.guarantors]),
    ]
    for table, values in rows:
        if not values:
            continue
        positioned = [ids | v | {"position": i} for i, v in enumerate(values)]
        try:
            transaction.write(sa.insert(table).values(positioned))
        except sa.exc.IntegrityError as exc:
            numbers = [v["number"] for v in values] if table is t.installment else []
            taken = sa.select(t.installment.c.id).where(
                t.installment.c.shop_id == receivable.shop_id.value,
                t.installment.c.number.in_(numbers),
            )
            if not numbers or not transaction.exists(taken):
                raise  # pas un numéro déjà pris : l'erreur remonte telle quelle
            raise duplicate(table.name, INSTALLMENT_NUMBER) from exc
