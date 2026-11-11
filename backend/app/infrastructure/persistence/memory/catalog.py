"""Dépôts mémoire du catalogue (T13) : articles (gabarit `MemoryRepository`) et historique des
prix (ajout seul, comme `MemoryAuditLog`). Même sémantique que l'adaptateur SQL (contrats)."""

import copy
from typing import cast

from app.application.catalog.ports import ArticleRepository, PriceHistoryLog
from app.application.catalog.search import ArticlePage, ArticlePageRequest, ArticleQuery, paginate
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId
from app.domain.catalog.prices import PriceHistory
from app.infrastructure.persistence.memory.database import Row
from app.infrastructure.persistence.memory.repository import MemoryRepository
from app.infrastructure.persistence.memory.shop_store import MemoryShopStore

STORED_VERSION = 1


class MemoryArticleRepository(MemoryRepository[ArticleId, Article], ArticleRepository):
    table = "articles"

    def _all(self) -> list[Article]:
        # Les lignes de cette table ne sont construites que par `_row` à partir d'un Article.
        rows = self._transaction.rows(self.table)
        articles = [cast(Article, copy.deepcopy(row.payload)) for row in rows]
        for article in articles:
            self._tracker.track(article, saved=False)
        return articles

    def find_by_key(self, constraint: str, key: str) -> Article | None:
        keys = {unique.name: unique for unique in self.unique_keys()}
        extract = keys[constraint].extract
        found = sorted(
            (article for article in self._all() if extract(article) == key),
            key=lambda article: article.id,
        )
        return found[0] if found else None

    def search(self, query: ArticleQuery, page: ArticlePageRequest) -> ArticlePage:
        return paginate([article for article in self._all() if query.matches(article)], page)


class MemoryPriceHistoryLog(MemoryShopStore, PriceHistoryLog):
    table = "price_history"

    def _append(self, entry: PriceHistory) -> None:
        row = Row(
            shop_id=entry.shop_id,
            entity_id=entry.id,
            version=STORED_VERSION,
            unique={},
            payload=entry,  # dataclass gelée : aucune copie à protéger
        )
        self._transaction.insert(self.table, row)

    def for_article(self, article_id: ArticleId) -> list[PriceHistory]:
        # Les lignes de cette table ne sont construites que par `_append`.
        entries = [cast(PriceHistory, row.payload) for row in self._transaction.rows(self.table)]
        mine = [entry for entry in entries if entry.article_id == article_id]
        return sorted(mine, key=lambda entry: (entry.effective_at, entry.id), reverse=True)


MEMORY_CATALOG_REPOSITORIES = (MemoryArticleRepository, MemoryPriceHistoryLog)
