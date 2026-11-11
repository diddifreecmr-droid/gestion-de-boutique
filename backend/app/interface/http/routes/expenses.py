"""Routes des dépenses (UC-DEP-01, 03, 04, 05) — specs § 6.3, sous `/shops/{shop_id}/…`.

- `GET /expenses` : liste du jour par défaut, filtres `from`, `to`, `category_id`, `tag_id`,
  `location_id`, `user_id` (auteur), `payment_mode_id`, pagination `cursor`/`limit`, totaux.
- `POST /expenses` : 201, ou 200 si l'`id` client existe déjà (rejeu idempotent, § 6.1) ;
  en-tête facultatif `X-Captured-At` (heure de l'appareil, RG-T04).
- `GET/PATCH /expenses/{id}`, `POST /expenses/{id}/cancel {reason}`,
  `GET /expenses/{id}/repeat` (brouillon de « Refaire cette dépense », rien n'est écrit).

Vendeur et chauffeur : 403 (journalisé) ; dépense d'une autre boutique : 404.
"""

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.application.expenses.use_cases.list_expenses import ExpenseCriteria
from app.application.expenses.use_cases.record_expense import RecordExpenseCommand
from app.application.ports.pagination import MAX_LIMIT, PageRequest
from app.application.security.actor import Actor
from app.domain.expenses.ids import ExpenseId, TagId
from app.domain.shared.ids import EntityId, UserId
from app.domain.shops.ids import ExpenseCategoryId, LocationId, PaymentModeId
from app.interface.http.presenters.expenses import (
    draft_response,
    expense_response,
    page_response,
)
from app.interface.http.routes.expense_components import ExpensesComponents
from app.interface.http.routes.expense_inputs import captured_at_of, input_of, patch_of
from app.interface.http.schemas.expenses import (
    ExpenseCancelRequest,
    ExpenseCreateRequest,
    ExpenseDraftResponse,
    ExpensePageResponse,
    ExpensePatch,
    ExpenseResponse,
)

IdQuery = Annotated[str | None, Query(max_length=64)]


def _optional[IdT: EntityId](kind: type[IdT], text: str | None) -> IdT | None:
    return None if text is None else kind.parse(text)


def build_expenses_router(expenses: ExpensesComponents) -> APIRouter:
    router = APIRouter(tags=["expenses"])
    Member = Annotated[Actor, Depends(expenses.guard.current_actor)]  # noqa: N806

    @router.get("/shops/{shop_id}/expenses")
    def list_expenses(
        actor: Member,
        first_day: Annotated[date | None, Query(alias="from")] = None,
        last_day: Annotated[date | None, Query(alias="to")] = None,
        category_id: IdQuery = None,
        tag_id: IdQuery = None,
        location_id: IdQuery = None,
        user_id: IdQuery = None,
        payment_mode_id: IdQuery = None,
        cursor: Annotated[str | None, Query(max_length=256)] = None,
        limit: Annotated[int | None, Query(ge=1, le=MAX_LIMIT)] = None,
    ) -> ExpensePageResponse:
        criteria = ExpenseCriteria(
            first_day=first_day,
            last_day=last_day,
            category_id=_optional(ExpenseCategoryId, category_id),
            tag_id=_optional(TagId, tag_id),
            location_id=_optional(LocationId, location_id),
            created_by=_optional(UserId, user_id),
            payment_mode_id=_optional(PaymentModeId, payment_mode_id),
        )
        listing = expenses.list.execute(actor, criteria, PageRequest.parse(cursor, limit))
        return page_response(listing)

    @router.post("/shops/{shop_id}/expenses", status_code=status.HTTP_201_CREATED)
    def record_expense(
        actor: Member,
        body: ExpenseCreateRequest,
        response: Response,
        x_captured_at: Annotated[datetime | None, Header()] = None,
    ) -> ExpenseResponse:
        command = RecordExpenseCommand(
            data=input_of(body),
            expense_id=_optional(ExpenseId, body.id),
            captured_at=captured_at_of(x_captured_at),
        )
        view, created = expenses.record.execute(actor, command)
        if not created:
            response.status_code = status.HTTP_200_OK
        return expense_response(view)

    @router.get("/shops/{shop_id}/expenses/{expense_id}")
    def get_expense(actor: Member, expense_id: str) -> ExpenseResponse:
        return expense_response(expenses.get.execute(actor, ExpenseId.parse(expense_id)))

    @router.patch("/shops/{shop_id}/expenses/{expense_id}")
    def correct_expense(actor: Member, expense_id: str, body: ExpensePatch) -> ExpenseResponse:
        view = expenses.correct.execute(
            actor, ExpenseId.parse(expense_id), patch_of(body), body.version
        )
        return expense_response(view)

    @router.post("/shops/{shop_id}/expenses/{expense_id}/cancel")
    def cancel_expense(
        actor: Member, expense_id: str, body: ExpenseCancelRequest
    ) -> ExpenseResponse:
        view = expenses.cancel.execute(actor, ExpenseId.parse(expense_id), body.reason)
        return expense_response(view)

    @router.get("/shops/{shop_id}/expenses/{expense_id}/repeat")
    def repeat_expense(actor: Member, expense_id: str) -> ExpenseDraftResponse:
        return draft_response(expenses.repeat.execute(actor, ExpenseId.parse(expense_id)))

    return router
