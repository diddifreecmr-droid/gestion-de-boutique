"""Point d'extension du tri « plus vendus » de la recherche d'articles (branché par T16).

Le catalogue ne connaît pas les ventes : le tri `BEST_SELLING` est délégué à un port
`SalesRanking` que le module Ventes fournira à la composition root. Tant qu'il n'est pas
branché, demander ce tri lève `SortUnavailable` (400) : jamais de repli silencieux sur l'ordre
alphabétique.
"""

from abc import ABC, abstractmethod
from enum import StrEnum

from app.application.catalog.search import ArticlePage, ArticlePageRequest, ArticleQuery
from app.application.ports.uow import UnitOfWork
from app.domain.shared.errors import ValidationFailed


class ArticleOrder(StrEnum):
    NAME = "name"
    BEST_SELLING = "best_selling"


class SortUnavailable(ValidationFailed):
    code = "SORT_UNAVAILABLE"

    def __init__(self, order: ArticleOrder) -> None:
        super().__init__("Ce tri n'est pas encore disponible", details={"sort": order.value})


class SalesRanking(ABC):
    """Fourni par le module Ventes : articles filtrés par `query`, du plus vendu au moins vendu."""

    @abstractmethod
    def search(
        self, uow: UnitOfWork, query: ArticleQuery, page: ArticlePageRequest
    ) -> ArticlePage: ...
