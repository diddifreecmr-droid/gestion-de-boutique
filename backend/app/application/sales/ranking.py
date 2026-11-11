"""Tri « plus vendus » de la recherche d'articles (UC-VEN-01 étape 2), port `SalesRanking`.

**Fenêtre glissante de 30 jours** (`WINDOW_DAYS`) avant l'instant de la recherche : quantités
de stock vendues par article, ventes **annulées exclues** (lecture `quantities_since`). Ordre :
quantité vendue décroissante, puis nom plié, puis identifiant — un article jamais vendu sur la
fenêtre arrive après, par ordre alphabétique. Les filtres (texte, statut) sont ceux de la
recherche du catalogue ; le curseur encode le rang (`ArticleCursor` opaque, même forme).
"""

from datetime import timedelta
from decimal import Decimal

from app.application.catalog.ports import ArticleRepository
from app.application.catalog.ranking import SalesRanking
from app.application.catalog.search import (
    ArticleCursor,
    ArticlePage,
    ArticlePageRequest,
    ArticleQuery,
)
from app.application.ports.clock import Clock
from app.application.ports.pagination import MAX_LIMIT
from app.application.ports.uow import UnitOfWork
from app.application.sales.ports import SaleRepository
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId

WINDOW_DAYS = 30
_RANK_CEILING = 10**14  # dixièmes de quantité : au-delà de toute quantité NUMERIC(12,1)


def rank_cursor(article: Article, sold: dict[ArticleId, Decimal]) -> ArticleCursor:
    tenths = int(sold.get(article.id, Decimal(0)) * 10)
    return ArticleCursor(
        f"{_RANK_CEILING - tenths:015d}~{article.details.sort_key}", article.id.value
    )


def all_matching(uow: UnitOfWork, query: ArticleQuery) -> list[Article]:
    articles = ArticleRepository.within(uow)
    found: list[Article] = []
    request = ArticlePageRequest(MAX_LIMIT)
    while True:
        page = articles.search(query, request)
        found.extend(page.items)
        if page.next_cursor is None:
            return found
        request = ArticlePageRequest(MAX_LIMIT, page.next_cursor)


class LedgerSalesRanking(SalesRanking):
    def __init__(self, clock: Clock, window_days: int = WINDOW_DAYS) -> None:
        if window_days < 1:
            msg = "Fenêtre du classement : au moins un jour"
            raise ValueError(msg)
        self._clock = clock
        self._window = timedelta(days=window_days)

    def search(self, uow: UnitOfWork, query: ArticleQuery, page: ArticlePageRequest) -> ArticlePage:
        sold = SaleRepository.within(uow).quantities_since(self._clock.now() - self._window)
        ranked = sorted(all_matching(uow, query), key=lambda a: rank_cursor(a, sold))
        after = page.after
        remaining = [a for a in ranked if after is None or rank_cursor(a, sold) > after]
        items = remaining[: page.limit]
        more = len(remaining) > page.limit
        cursor = rank_cursor(items[-1], sold) if more and items else None
        return ArticlePage(items, cursor)
