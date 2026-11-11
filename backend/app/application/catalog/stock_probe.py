"""Port `ArticleStock` : un article a-t-il encore du stock ? (UC-STK-04, recette CAT-12).

« Un article qui a encore du stock (dans un lieu ou en route) ne peut pas être archivé. »
Implémenté par le module Stock (T14) sur sa projection `stock_level`, dans la transaction de
l'unité de travail reçue : `application/stock/probes.py` (`LedgerArticleStock`), branché par
`bootstrap/catalog.py`. L'implémentation provisoire de T13 a été retirée.
"""

from abc import ABC, abstractmethod

from app.application.ports.uow import UnitOfWork
from app.domain.catalog.ids import ArticleId


class ArticleStock(ABC):
    @abstractmethod
    def has_stock(self, uow: UnitOfWork, article_id: ArticleId) -> bool:
        """Vrai si une quantité non nulle (vendable, abîmée ou en route) existe quelque part."""
