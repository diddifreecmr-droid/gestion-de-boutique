"""Ports du catalogue et des lieux implémentés sur la projection du stock (remplacent les
implémentations provisoires de T10/T13).

- `LedgerArticleStock` (UC-STK-04, CAT-12) : un article qui a une quantité non nulle —
  vendable, abîmée **ou en route** — dans un lieu ne peut pas être archivé.
- `LedgerLocationStock` (UC-SOC-05, LOC-02) : un lieu qui a du stock (y compris en route vers
  lui) ne peut pas être désactivé.
- `LedgerStockBadges` (2026-11-15) : pastille de stock des articles d'une liste, sans quantité.

Tous lisent `stock_level` dans la transaction de l'unité de travail reçue.
"""

from collections.abc import Mapping, Sequence
from decimal import Decimal

from app.application.catalog.stock_probe import ArticleStock, ArticleStockBadges
from app.application.ports.uow import UnitOfWork
from app.application.shops.stock_probe import LocationStock
from app.application.stock.ports import StockLevelRepository
from app.application.stock.use_cases.stock_matrix import badge_for
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId
from app.domain.shops.ids import LocationId


class LedgerArticleStock(ArticleStock):
    def has_stock(self, uow: UnitOfWork, article_id: ArticleId) -> bool:
        levels = StockLevelRepository.within(uow).for_article(article_id)
        return any(level.has_stock for level in levels)


class LedgerLocationStock(LocationStock):
    def has_stock(self, uow: UnitOfWork, location_id: LocationId) -> bool:
        levels = StockLevelRepository.within(uow).for_location(location_id)
        return any(level.has_stock for level in levels)


class LedgerStockBadges(ArticleStockBadges):
    """Une lecture de `stock_level` pour toute la page."""

    def badges(
        self, uow: UnitOfWork, articles: Sequence[Article], shop_threshold: Decimal
    ) -> Mapping[ArticleId, str]:
        totals: dict[ArticleId, Decimal] = {article.id: Decimal(0) for article in articles}
        for level in StockLevelRepository.within(uow).list_all():
            if level.article_id in totals:
                totals[level.article_id] += level.sellable.value
        return {
            article.id: badge_for(
                totals[article.id], article.details.effective_threshold(shop_threshold)
            ).value
            for article in articles
        }
