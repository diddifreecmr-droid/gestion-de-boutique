"""UC-STK-06 — Historique d'un article ; UC-TRF-05 (lecture) — stock abîmé par lieu.

- Historique (`STOCK_HISTORY_READ` : propriétaire, comptable ; vendeur 403, STK-05) : tous les
  mouvements de l'article, du plus récent au plus ancien (date de l'opération), paginés par
  curseur : type, lieu, quantité signée, état, stock après, document lié, auteur, coût
  unitaire (qui voit les coûts). Document d'une vente montré au comptable **sans** numéro ni
  identifiant (RG-D03, Q-39).
- Stock abîmé (`STOCK_VALUE_READ`, M08) : projections dont la quantité abîmée est non nulle.
"""

from dataclasses import dataclass

from app.application.catalog.ports import ArticleRepository
from app.application.ports.pagination import Page, PageRequest
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.application.stock.ports import StockLevelRepository, StockMovementLog
from app.application.stock.reading import articles_by_id, locations_by_id
from app.application.stock.visibility import StockVisibility, stock_visibility
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId
from app.domain.shops.ids import LocationId
from app.domain.shops.location import Location
from app.domain.stock.level import StockLevel
from app.domain.stock.movement import StockMovement


@dataclass(frozen=True, slots=True, kw_only=True)
class MovementHistory:
    article: Article
    page: Page[StockMovement]
    locations: dict[LocationId, Location]
    visibility: StockVisibility


@dataclass(frozen=True, slots=True, kw_only=True)
class DamagedLine:
    article: Article
    location: Location
    level: StockLevel


@dataclass(frozen=True, slots=True, kw_only=True)
class DamagedStock:
    lines: list[DamagedLine]
    visibility: StockVisibility


class ReadArticleMovements:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy) -> None:
        self._uow_factory = uow_factory
        self._policy = policy

    def execute(self, actor: Actor, article_id: ArticleId, page: PageRequest) -> MovementHistory:
        self._policy.require(actor, Permission.STOCK_HISTORY_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            article = ArticleRepository.within(uow).get(article_id)
            found = StockMovementLog.within(uow).for_article(article.id, page)
            locations = locations_by_id(uow)
        return MovementHistory(
            article=article,
            page=found,
            locations=locations,
            visibility=stock_visibility(self._policy, actor),
        )


class ReadDamagedStock:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy) -> None:
        self._uow_factory = uow_factory
        self._policy = policy

    def execute(self, actor: Actor) -> DamagedStock:
        self._policy.require(actor, Permission.STOCK_VALUE_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            levels = StockLevelRepository.within(uow).list_all()
            articles = articles_by_id(uow)
            locations = locations_by_id(uow)
        order = {location_id: rank for rank, location_id in enumerate(locations)}
        lines = [
            DamagedLine(
                article=articles[lv.article_id], location=locations[lv.location_id], level=lv
            )
            for lv in levels
            if lv.damaged.value != 0
        ]
        lines.sort(key=lambda line: (order[line.location.id], line.article.details.sort_key))
        return DamagedStock(lines=lines, visibility=stock_visibility(self._policy, actor))
