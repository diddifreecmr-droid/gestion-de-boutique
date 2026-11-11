"""Données de contrat du module Dépenses : dépenses et tags construits par le domaine seul."""

from datetime import UTC, date, datetime, timedelta

from app.domain.audit.values import Performer
from app.domain.expenses.details import Capture, ExpenseDetails
from app.domain.expenses.expense import Expense
from app.domain.expenses.ids import TagId
from app.domain.expenses.tag import Tag
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.shops.ids import ExpenseCategoryId, PaymentModeId

T = datetime(2026, 11, 10, 14, 0, tzinfo=UTC)
DAY = date(2026, 11, 10)
AUTHOR = UserId.new()
DEVICE = DeviceId.new()
CATEGORY = ExpenseCategoryId.new()
OTHER_CATEGORY = ExpenseCategoryId.new()
CASH = PaymentModeId.new()
WHO_PERFORMER = Performer(AUTHOR, "accountant", DEVICE)


def tag(shop_id: ShopId, name: str) -> Tag:
    return Tag.create(shop_id, name, performer=WHO_PERFORMER, now=T)


def expense(
    shop_id: ShopId,
    sequence: int,
    *,
    amount: int = 1_000,
    spent_on: date = DAY,
    category: ExpenseCategoryId = CATEGORY,
    tags: tuple[TagId, ...] = (),
    minutes: int = 0,
    author: UserId = AUTHOR,
) -> Expense:
    at = T + timedelta(minutes=minutes)
    details = ExpenseDetails(
        spent_on=spent_on,
        amount=amount,
        category_id=category,
        payment_mode_id=CASH,
        tag_ids=tags,
    )
    return Expense.record(
        shop_id,
        DocNumber(DocType.EXPENSE, sequence),
        details,
        Capture(author, DEVICE, at - timedelta(seconds=30), at),
        performer=WHO_PERFORMER,
    )
