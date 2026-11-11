"""Routes du catalogue `/shops/{id}/articles` (UC-STK-01 à UC-STK-04, specs § 6.3).

Création : 201, ou 200 si l'`id` fourni existe déjà (rejeu idempotent, § 6.1). Chaque réponse
est la fiche relue **avec les droits de l'acteur** (`GetArticle`) : un comptable qui crée un
article ne reçoit pas plus de prix qu'en lecture. Clés invisibles absentes du JSON (TR-05).
"""

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status

from app.application.catalog.ranking import ArticleOrder
from app.application.catalog.search import ArticlePageRequest, ArticleQuery
from app.application.catalog.use_cases.archive_article import ArchiveArticle
from app.application.catalog.use_cases.context import ArticleInput
from app.application.catalog.use_cases.create_article import CreateArticle, CreateArticleCommand
from app.application.catalog.use_cases.read_articles import GetArticle, SearchArticles
from app.application.catalog.use_cases.set_prices import SetArticlePrices
from app.application.catalog.use_cases.update_article import UpdateArticle
from app.application.security.actor import Actor
from app.domain.catalog.details import ArticleStatus
from app.domain.catalog.ids import ArticleId, AttachmentId
from app.domain.catalog.prices import ArticlePrices
from app.domain.shared.money import Money
from app.interface.http.presenters.catalog import list_response, sheet_response
from app.interface.http.schemas.catalog import (
    ArticleCreateRequest,
    ArticleListResponse,
    ArticlePatch,
    ArticleResponse,
    PricesRequest,
)
from app.interface.http.security import AuthGuard

ALL_STATUSES = "all"


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogComponents:
    create: CreateArticle
    update: UpdateArticle
    prices: SetArticlePrices
    archive: ArchiveArticle
    search: SearchArticles
    get: GetArticle
    guard: AuthGuard


def _prices(body: ArticleCreateRequest | PricesRequest) -> ArticlePrices:
    def money(value: int | None) -> Money | None:
        return None if value is None else Money(value)

    return ArticlePrices(
        base_price=money(body.base_price),
        base_price_piece=money(body.base_price_piece),
        min_price=money(body.min_price),
        min_price_piece=money(body.min_price_piece),
    )


def _photo(text: str | None) -> AttachmentId | None:
    return None if text is None else AttachmentId.parse(text)


def _patch(body: ArticlePatch) -> dict[str, Any]:
    patch: dict[str, Any] = dict(body.fields)
    for name in ("alert_threshold", "photo_id", "notes"):
        if name in body.model_fields_set:
            patch[name] = getattr(body, name)
    if "photo_id" in patch:
        patch["photo_id"] = _photo(patch["photo_id"])
    return patch


def build_catalog_router(catalog: CatalogComponents) -> APIRouter:
    router = APIRouter(tags=["catalog"])
    Member = Annotated[Actor, Depends(catalog.guard.current_actor)]  # noqa: N806
    sparse: dict[str, Any] = {"response_model_exclude_unset": True}

    def sheet(actor: Actor, article_id: ArticleId) -> ArticleResponse:
        return sheet_response(catalog.get.execute(actor, article_id))

    @router.get("/shops/{shop_id}/articles", **sparse)
    def search_articles(
        actor: Member,
        q: Annotated[str | None, Query(max_length=100)] = None,
        status_filter: Annotated[str, Query(alias="status", pattern="^(active|archived|all)$")] = (
            "active"
        ),
        sort: ArticleOrder = ArticleOrder.NAME,
        cursor: Annotated[str | None, Query(max_length=512)] = None,
        limit: int | None = None,
    ) -> ArticleListResponse:
        wanted = None if status_filter == ALL_STATUSES else ArticleStatus(status_filter)
        found = catalog.search.execute(
            actor, ArticleQuery(q, wanted), ArticlePageRequest.parse(cursor, limit), sort
        )
        return list_response(found)

    @router.post("/shops/{shop_id}/articles", status_code=status.HTTP_201_CREATED, **sparse)
    def create_article(
        actor: Member, body: ArticleCreateRequest, response: Response
    ) -> ArticleResponse:
        data = ArticleInput(
            fields=dict(body.fields),
            alert_threshold=body.alert_threshold,
            photo_id=_photo(body.photo_id),
            notes=body.notes,
        )
        command = CreateArticleCommand(
            data=data,
            prices=_prices(body),
            article_id=None if body.id is None else ArticleId.parse(body.id),
        )
        article, created = catalog.create.execute(actor, command)
        if not created:
            response.status_code = status.HTTP_200_OK
        return sheet(actor, article.id)

    @router.get("/shops/{shop_id}/articles/{article_id}", **sparse)
    def get_article(actor: Member, article_id: str) -> ArticleResponse:
        return sheet(actor, ArticleId.parse(article_id))

    @router.patch("/shops/{shop_id}/articles/{article_id}", **sparse)
    def patch_article(actor: Member, article_id: str, body: ArticlePatch) -> ArticleResponse:
        ident = ArticleId.parse(article_id)
        catalog.update.execute(actor, ident, _patch(body), body.version, body.reason)
        return sheet(actor, ident)

    @router.put("/shops/{shop_id}/articles/{article_id}/prices", **sparse)
    def put_prices(actor: Member, article_id: str, body: PricesRequest) -> ArticleResponse:
        ident = ArticleId.parse(article_id)
        catalog.prices.execute(actor, ident, _prices(body), body.version)
        return sheet(actor, ident)

    @router.post("/shops/{shop_id}/articles/{article_id}/archive", **sparse)
    def archive_article(actor: Member, article_id: str) -> ArticleResponse:
        ident = ArticleId.parse(article_id)
        catalog.archive.archive(actor, ident)
        return sheet(actor, ident)

    @router.post("/shops/{shop_id}/articles/{article_id}/reactivate", **sparse)
    def reactivate_article(actor: Member, article_id: str) -> ArticleResponse:
        ident = ArticleId.parse(article_id)
        catalog.archive.reactivate(actor, ident)
        return sheet(actor, ident)

    return router
