"""Recherche d'articles et fiche article (UC-STK-05 côté catalogue, UC-STK-06 « fiche »).

Lecture : quiconque voit le stock (`STOCK_READ` : propriétaire, comptable, vendeur ; chauffeur
refusé). Ce que chacun voit des prix est décidé par `visibility.py` (TR-05) et appliqué par le
présentateur : le vendeur ne reçoit jamais `last_cost` ni `wac` (RG-D02). La fiche porte aussi
le seuil d'alerte appliqué (celui de l'article ou de la boutique) et l'historique des prix pour
qui peut le voir. L'historique des **mouvements** de la fiche arrive avec le module Stock (T14).
Sur demande (`with_thumbnails`), la liste porte un lien signé court par photo d'article, délivré
après contrôle des droits, dans la même unité de travail (`thumbnails.py`, UC-PAP-02).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from app.application.attachments.links import SignedLink
from app.application.catalog.ports import ArticleRepository, PriceHistoryLog
from app.application.catalog.ranking import ArticleOrder, SalesRanking, SortUnavailable
from app.application.catalog.search import ArticlePage, ArticlePageRequest, ArticleQuery
from app.application.catalog.thumbnails import ArticleThumbnails, ThumbnailsUnavailable
from app.application.catalog.use_cases.context import shop_context
from app.application.catalog.visibility import READ_PERMISSION, CatalogVisibility, visibility_for
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId
from app.domain.catalog.prices import PriceHistory


@dataclass(frozen=True, slots=True, kw_only=True)
class ArticleList:
    page: ArticlePage
    visibility: CatalogVisibility
    min_price_enabled: bool
    shop_threshold: Decimal
    thumbnails: Mapping[ArticleId, SignedLink | None] | None = None
    """Lien de la photo de chaque article de la page ; `None` si non demandé."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ArticleSheet:
    article: Article
    visibility: CatalogVisibility
    min_price_enabled: bool
    shop_threshold: Decimal
    price_history: list[PriceHistory]
    """Vide pour qui ne voit pas l'historique des prix."""


class SearchArticles:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        policy: Policy,
        ranking: SalesRanking | None = None,
        thumbnails: ArticleThumbnails | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._ranking = ranking
        self._thumbnails = thumbnails

    def execute(
        self,
        actor: Actor,
        query: ArticleQuery,
        page: ArticlePageRequest,
        order: ArticleOrder = ArticleOrder.NAME,
        *,
        with_thumbnails: bool = False,
    ) -> ArticleList:
        self._policy.require(actor, READ_PERMISSION)
        if order is ArticleOrder.BEST_SELLING and self._ranking is None:
            raise SortUnavailable(order)
        if with_thumbnails and self._thumbnails is None:
            raise ThumbnailsUnavailable
        thumbnails = None
        with self._uow_factory(actor_shop(actor)) as uow:
            settings = shop_context(uow).settings
            if order is ArticleOrder.BEST_SELLING and self._ranking is not None:
                found = self._ranking.search(uow, query, page)
            else:
                found = ArticleRepository.within(uow).search(query, page)
            if with_thumbnails and self._thumbnails is not None:
                thumbnails = self._thumbnails.issue(uow, actor, found.items)
        return ArticleList(
            page=found,
            visibility=visibility_for(self._policy, actor),
            min_price_enabled=settings.min_price_enabled,
            shop_threshold=settings.low_stock_threshold,
            thumbnails=thumbnails,
        )


class GetArticle:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy) -> None:
        self._uow_factory = uow_factory
        self._policy = policy

    def execute(self, actor: Actor, article_id: ArticleId) -> ArticleSheet:
        self._policy.require(actor, READ_PERMISSION)
        visibility = visibility_for(self._policy, actor)
        with self._uow_factory(actor_shop(actor)) as uow:
            article = ArticleRepository.within(uow).get(article_id)
            settings = shop_context(uow).settings
            history = (
                PriceHistoryLog.within(uow).for_article(article.id)
                if visibility.price_history
                else []
            )
        return ArticleSheet(
            article=article,
            visibility=visibility,
            min_price_enabled=settings.min_price_enabled,
            shop_threshold=settings.low_stock_threshold,
            price_history=history,
        )
