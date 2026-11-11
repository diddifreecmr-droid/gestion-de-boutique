"""Lectures communes aux écrans de stock : articles du catalogue et lieux.

Volume visé au Lot 1 : quelques centaines d'articles par boutique ; la matrice et la valeur du
stock lisent donc **tous** les articles (par pages de `MAX_LIMIT`) et toutes les projections
(specs § 10 : lecture de `stock_level`, jamais la somme des mouvements).
"""

from app.application.catalog.ports import ArticleRepository
from app.application.catalog.search import ArticlePageRequest, ArticleQuery
from app.application.ports.pagination import MAX_LIMIT
from app.application.ports.uow import UnitOfWork
from app.application.shops.ports import LocationRepository
from app.domain.catalog.article import Article
from app.domain.catalog.details import ArticleStatus
from app.domain.catalog.ids import ArticleId
from app.domain.shops.ids import LocationId
from app.domain.shops.location import Location

MAX_PAGES = 1000  # garde-fou : 200 000 articles, bien au-delà du volume visé


def all_articles(
    uow: UnitOfWork, text: str | None = None, status: ArticleStatus | None = None
) -> list[Article]:
    """Articles filtrés (`ArticleQuery`), par nom ; toutes les pages."""
    repository = ArticleRepository.within(uow)
    query = ArticleQuery(text, status)
    found: list[Article] = []
    request = ArticlePageRequest(MAX_LIMIT)
    for _ in range(MAX_PAGES):
        page = repository.search(query, request)
        found.extend(page.items)
        if page.next_cursor is None:
            return found
        request = ArticlePageRequest(MAX_LIMIT, page.next_cursor)
    msg = f"Plus de {MAX_PAGES} pages d'articles : volume hors des hypothèses du Lot 1"
    raise RuntimeError(msg)


def articles_by_id(uow: UnitOfWork) -> dict[ArticleId, Article]:
    return {article.id: article for article in all_articles(uow)}


def locations_by_id(uow: UnitOfWork) -> dict[LocationId, Location]:
    """Tous les lieux (inactifs compris), dans l'ordre d'affichage."""
    return {location.id: location for location in LocationRepository.within(uow).list_all()}
