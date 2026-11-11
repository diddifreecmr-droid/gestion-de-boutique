"""Port `ArticleStock` : un article a-t-il encore du stock ? (UC-STK-04, recette CAT-12).

« Un article qui a encore du stock (dans un lieu ou en route) ne peut pas être archivé. » Le
stock n'existe qu'avec le module Stock (T14), qui implémentera ce port sur sa projection
`stock_level`, dans la transaction de l'unité de travail reçue.

**PROVISOIRE (T13 → T14)** : `NoArticleStockRecorded` répond toujours « aucun stock », ce qui
est exact tant qu'aucun mouvement de stock ne peut être enregistré. La composition root
(`bootstrap/catalog.py`) le remplacera par l'adaptateur de T14 ; il ne doit pas lui survivre.
"""

from abc import ABC, abstractmethod

from app.application.ports.uow import UnitOfWork
from app.domain.catalog.ids import ArticleId


class ArticleStock(ABC):
    @abstractmethod
    def has_stock(self, uow: UnitOfWork, article_id: ArticleId) -> bool:
        """Vrai si une quantité non nulle (vendable, abîmée ou en route) existe quelque part."""


class NoArticleStockRecorded(ArticleStock):
    """PROVISOIRE jusqu'à T14 : aucun mouvement de stock n'existe encore."""

    def has_stock(self, uow: UnitOfWork, article_id: ArticleId) -> bool:
        return False
