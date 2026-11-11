"""Présentation des dépenses, catégories et tags (TR-05).

Seuls le propriétaire et le comptable atteignent ces routes (`EXPENSE_READ`) : aucun champ
n'est à masquer selon le rôle. `editable` et `correction_deadline` disent au frontend si les
boutons « Modifier » et « Annuler » s'affichent (le serveur revérifie à chaque action).
"""

from collections.abc import Iterable

from app.application.expenses.ports import ExpenseTotals
from app.application.expenses.use_cases.list_expenses import ExpenseListing
from app.application.expenses.use_cases.repeat_expense import DraftView
from app.application.expenses.views import ExpenseView
from app.domain.expenses.tag import Tag
from app.domain.shops.expense_category import ExpenseCategory
from app.interface.http.schemas.expenses import (
    CancellationResponse,
    CategoryTotalResponse,
    ExpenseCategoryResponse,
    ExpenseDraftResponse,
    ExpensePageResponse,
    ExpenseResponse,
    TagResponse,
    TotalsResponse,
)


def _text(value: object) -> str | None:
    return None if value is None else str(value)


def tag_response(tag: Tag) -> TagResponse:
    return TagResponse(id=str(tag.id), name=tag.name)


def _tags(tags: Iterable[Tag]) -> list[TagResponse]:
    return [tag_response(tag) for tag in tags]


def expense_response(view: ExpenseView) -> ExpenseResponse:
    expense = view.expense
    details, capture, cancel = expense.details, expense.capture, expense.cancellation
    return ExpenseResponse(
        id=str(expense.id),
        number=str(expense.number),
        spent_on=details.spent_on,
        amount=details.amount,
        category_id=str(details.category_id),
        payment_mode_id=str(details.payment_mode_id),
        tags=_tags(view.tags),
        description=details.description,
        location_id=_text(details.location_id),
        beneficiary=details.beneficiary,
        attachment_id=_text(details.attachment_id),
        status=expense.status.value,
        created_by=str(capture.created_by),
        device_id=str(capture.device_id),
        captured_at=capture.captured_at,
        received_at=capture.received_at,
        cancellation=None
        if cancel is None
        else CancellationResponse(
            cancelled_at=cancel.at, cancelled_by=str(cancel.by), reason=cancel.reason
        ),
        editable=view.editable,
        correction_deadline=expense.correction_deadline,
        version=expense.version,
    )


def totals_response(totals: ExpenseTotals) -> TotalsResponse:
    return TotalsResponse(
        amount=totals.amount,
        count=totals.count,
        by_category=[
            CategoryTotalResponse(
                category_id=str(total.category_id), amount=total.amount, count=total.count
            )
            for total in totals.by_category
        ],
    )


def page_response(listing: ExpenseListing) -> ExpensePageResponse:
    cursor = listing.next_cursor
    return ExpensePageResponse(
        items=[expense_response(view) for view in listing.items],
        next_cursor=None if cursor is None else cursor.encode(),
        first_day=listing.first_day,
        last_day=listing.last_day,
        totals=totals_response(listing.totals),
    )


def draft_response(view: DraftView) -> ExpenseDraftResponse:
    draft = view.draft
    return ExpenseDraftResponse(
        spent_on=draft.spent_on,
        amount=draft.amount,
        category_id=str(draft.category_id),
        tags=_tags(view.tags),
        beneficiary=draft.beneficiary,
    )


def category_response(category: ExpenseCategory) -> ExpenseCategoryResponse:
    return ExpenseCategoryResponse(
        id=str(category.id),
        name=category.name,
        is_base=category.is_base,
        active=category.active,
        requires_description=category.requires_description,
        display_order=category.display_order,
        version=category.version,
    )
