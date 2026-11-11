"""Ports du catalogue (T13) : dépôt des articles, historique des prix en ajout seul.

- `ArticleRepository` (gabarit `Repository`, `Port.within(uow)`) : deux unicités par boutique,
  marque + modèle et référence, sur les clés pliées ; leurs noms sont ceux des contraintes SQL
  (`tables_catalog.py`). `find_by_key` sert à **proposer** l'article existant (UC-STK-01).
- `PriceHistoryLog` : historique des prix (UC-STK-03), sans `update` ni suppression, comme le
  journal ; écrit dans la transaction du changement de prix.
"""

from abc import abstractmethod
from collections.abc import Sequence

from app.application.catalog.search import ArticlePage, ArticlePageRequest, ArticleQuery
from app.application.ports.aggregate import UniqueKey
from app.application.ports.errors import IsolationViolation
from app.application.ports.shop_bound import ShopBoundPort
from app.application.shops.ports import ShopRecordRepository
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId
from app.domain.catalog.prices import PriceHistory

ARTICLE_BRAND_MODEL = "article_brand_model"
ARTICLE_REFERENCE = "article_reference"


class ArticleRepository(ShopRecordRepository[ArticleId, Article]):
    def unique_keys(self) -> Sequence[UniqueKey[Article]]:
        return (
            UniqueKey(ARTICLE_BRAND_MODEL, lambda article: article.details.brand_model_key),
            UniqueKey(ARTICLE_REFERENCE, lambda article: article.details.reference_key),
        )

    @abstractmethod
    def find_by_key(self, constraint: str, key: str) -> Article | None:
        """Article dont la clé pliée de la contrainte `constraint` vaut `key`, ou `None`."""

    @abstractmethod
    def search(self, query: ArticleQuery, page: ArticlePageRequest) -> ArticlePage:
        """Articles filtrés, par nom plié puis identifiant (`search.py`)."""


class PriceHistoryLog(ShopBoundPort):
    """Historique des prix de la boutique, en ajout seul."""

    def append(self, entry: PriceHistory) -> None:
        if entry.shop_id != self.shop_id:
            msg = "Historique de prix d'une autre boutique"
            raise IsolationViolation(msg)
        self._append(entry)

    @abstractmethod
    def for_article(self, article_id: ArticleId) -> list[PriceHistory]:
        """Lignes de l'article, de la plus récente à la plus ancienne."""

    @abstractmethod
    def _append(self, entry: PriceHistory) -> None: ...
