"""Listes déroulantes des modèles, lues dans la boutique au téléchargement (IMP-01).

- `locations` : lieux **actifs**, dans l'ordre d'affichage (liste stricte) ;
- `categories` : catégories déjà saisies sur les articles actifs (liste indicative : une
  catégorie nouvelle reste permise) ;
- `customer_kinds` : « Particulier », « Entreprise » (liste stricte).

Lecture seule, dans l'unité de travail du téléchargement ; rien n'est écrit.
"""

from collections.abc import Mapping
from types import MappingProxyType

from app.application.catalog.ports import ArticleRepository
from app.application.catalog.search import ArticlePageRequest, ArticleQuery
from app.application.imports.workbook import LIST_MAX, ChoiceList
from app.application.ports.pagination import MAX_LIMIT
from app.application.ports.uow import UnitOfWork
from app.application.shops.ports import LocationRepository
from app.domain.imports.columns import ChoiceSource
from app.domain.sales.customer import CustomerKind

CATEGORY_ATTRIBUTE = "category"
CUSTOMER_KIND_LABELS: Mapping[str, CustomerKind] = MappingProxyType(
    {"Particulier": CustomerKind.INDIVIDUAL, "Entreprise": CustomerKind.COMPANY}
)
"""Libellé de la liste → type de client (repris par le modèle Clients, T34)."""
_TITLES = {
    ChoiceSource.LOCATIONS: "Lieux",
    ChoiceSource.CATEGORIES: "Catégories",
    ChoiceSource.CUSTOMER_KINDS: "Types de client",
}


def _locations(uow: UnitOfWork) -> tuple[str, ...]:
    found = [loc for loc in LocationRepository.within(uow).list_all() if loc.details.active]
    found.sort(key=lambda loc: (loc.details.display_order, loc.name.casefold()))
    return tuple(loc.name for loc in found)[:LIST_MAX]


def _categories(uow: UnitOfWork) -> tuple[str, ...]:
    articles = ArticleRepository.within(uow)
    seen: dict[str, str] = {}
    page = articles.search(ArticleQuery(), ArticlePageRequest(MAX_LIMIT))
    while True:
        for article in page.items:
            value = article.details.fields.attributes.get(CATEGORY_ATTRIBUTE)
            if isinstance(value, str) and value.strip():
                seen.setdefault(value.strip().casefold(), value.strip())
        if page.next_cursor is None or len(seen) >= LIST_MAX:
            break
        page = articles.search(ArticleQuery(), ArticlePageRequest(MAX_LIMIT, page.next_cursor))
    return tuple(sorted(seen.values(), key=str.casefold))[:LIST_MAX]


def choice_list(uow: UnitOfWork, source: ChoiceSource) -> ChoiceList:
    source = ChoiceSource(source)
    if source is ChoiceSource.LOCATIONS:
        values, strict = _locations(uow), True
    elif source is ChoiceSource.CATEGORIES:
        values, strict = _categories(uow), False
    else:
        values, strict = tuple(CUSTOMER_KIND_LABELS), True
    return ChoiceList(source=source, title=_TITLES[source], values=values, strict=strict)
