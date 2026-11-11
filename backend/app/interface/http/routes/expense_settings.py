"""Routes des catégories de dépense et des tags (UC-DEP-02) — specs § 6.3.

- `GET /expense-categories` : comptable (actives) et propriétaire (toutes) ;
  `POST` (201, ou 200 si l'`id` client existe) et `PATCH /{id}` (`version`) : propriétaire.
- `GET /tags?search=` : tags non fusionnés (comptable, propriétaire).
- `POST /tags/merge {source_id, target_id}` : propriétaire seul (recette EXP-04, M24).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.application.expenses.use_cases.manage_expense_categories import CategoryPatch
from app.application.security.actor import Actor
from app.domain.expenses.ids import TagId
from app.domain.shops.ids import ExpenseCategoryId
from app.interface.http.presenters.expenses import category_response, tag_response
from app.interface.http.routes.expense_components import ExpensesComponents
from app.interface.http.schemas.expenses import (
    ExpenseCategoryCreateRequest,
    ExpenseCategoryPatch,
    ExpenseCategoryResponse,
    TagMergeRequest,
    TagMergeResponse,
    TagResponse,
)


def build_expense_settings_router(expenses: ExpensesComponents) -> APIRouter:
    router = APIRouter(tags=["expenses"])
    Member = Annotated[Actor, Depends(expenses.guard.current_actor)]  # noqa: N806

    @router.get("/shops/{shop_id}/expense-categories")
    def list_categories(actor: Member) -> list[ExpenseCategoryResponse]:
        return [category_response(c) for c in expenses.categories.list(actor)]

    @router.post("/shops/{shop_id}/expense-categories", status_code=status.HTTP_201_CREATED)
    def create_category(
        actor: Member, body: ExpenseCategoryCreateRequest, response: Response
    ) -> ExpenseCategoryResponse:
        category_id = None if body.id is None else ExpenseCategoryId.parse(body.id)
        category, created = expenses.categories.create(
            actor, body.name, body.display_order, category_id
        )
        if not created:
            response.status_code = status.HTTP_200_OK
        return category_response(category)

    @router.patch("/shops/{shop_id}/expense-categories/{category_id}")
    def patch_category(
        actor: Member, category_id: str, body: ExpenseCategoryPatch
    ) -> ExpenseCategoryResponse:
        patch = CategoryPatch(name=body.name, active=body.active, display_order=body.display_order)
        category = expenses.categories.update(
            actor, ExpenseCategoryId.parse(category_id), patch, body.version
        )
        return category_response(category)

    @router.get("/shops/{shop_id}/tags")
    def list_tags(
        actor: Member, search: Annotated[str | None, Query(max_length=40)] = None
    ) -> list[TagResponse]:
        return [tag_response(tag) for tag in expenses.tags.execute(actor, search)]

    @router.post("/shops/{shop_id}/tags/merge")
    def merge_tags(actor: Member, body: TagMergeRequest) -> TagMergeResponse:
        result = expenses.merge_tags.execute(
            actor, TagId.parse(body.source_id), TagId.parse(body.target_id)
        )
        return TagMergeResponse(
            target=tag_response(result.target), retagged_expenses=result.retagged_expenses
        )

    return router
