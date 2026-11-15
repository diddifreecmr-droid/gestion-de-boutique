"""Ports du catalogue servis par le module Stock (T14).

- `ArticleStock` (UC-STK-04, recette CAT-12) : « Un article qui a encore du stock (dans un
  lieu ou en route) ne peut pas être archivé. »
- `ArticleStockBadges` (décision client du 2026-11-15) : à la vente, l'employé ne voit qu'une
  **pastille** (vert `ok`, orange `low`, rouge `out`), jamais une quantité ; même règle que la
  matrice du stock (`stock_matrix.badge_for` : vendable tous lieux, seuil appliqué).

Implémentés sur la projection `stock_level`, dans la transaction de l'unité de travail reçue :
`application/stock/probes.py`, branchés par `bootstrap/catalog.py`.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from decimal import Decimal

from app.application.ports.uow import UnitOfWork
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId


class ArticleStock(ABC):
    @abstractmethod
    def has_stock(self, uow: UnitOfWork, article_id: ArticleId) -> bool:
        """Vrai si une quantité non nulle (vendable, abîmée ou en route) existe quelque part."""


class ArticleStockBadges(ABC):
    @abstractmethod
    def badges(
        self, uow: UnitOfWork, articles: Sequence[Article], shop_threshold: Decimal
    ) -> Mapping[ArticleId, str]:
        """Pastille (`ok` | `low` | `out`) de chacun des articles reçus."""
