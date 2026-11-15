"""Aides des cas d'utilisation « tissu » (Textile, un article par couleur, 2026-11-15).

- `require_fabrics` : seul un profil qui a le champ « Tissu » (Textile) gère des tissus ;
  ailleurs → `ValidationFailed` (400) sur `fabric`.
- `fabric_articles` : toutes les couleurs d'un tissu (comparaison pliée), page après page,
  hors articles retirés par l'annulation de leur import (QC-6).
- `create_colors` : crée l'article de chaque couleur dans l'unité de travail reçue (aucun
  `commit`) : doublon de nom → `DuplicateArticle` (409) qui désigne l'article existant ;
  référence générée ; prix fixés et inscrits à l'historique.
- `FabricView` : articles + ce que l'acteur peut en voir (présentés comme la liste).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.application.catalog.ports import ArticleRepository
from app.application.catalog.search import ArticlePageRequest, ArticleQuery
from app.application.catalog.use_cases.context import (
    ArticleInput,
    ShopCatalogContext,
    build_details,
    ensure_reference,
    record_history,
    require_unique,
)
from app.application.catalog.visibility import CatalogVisibility
from app.application.ports.pagination import MAX_LIMIT
from app.application.ports.uow import UnitOfWork
from app.domain.audit.values import Performer
from app.domain.catalog.article import Article
from app.domain.catalog.fabric import FabricShape, color_fields
from app.domain.catalog.prices import ArticlePrices
from app.domain.profiles.profile import ShopProfile
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import UserId


@dataclass(frozen=True, slots=True, kw_only=True)
class FabricTerms:
    """Ce que reçoit chaque nouvelle couleur d'un tissu."""

    shape: FabricShape
    alert_threshold: Decimal | None = None
    prices: ArticlePrices | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class FabricView:
    fabric: str
    articles: list[Article]
    visibility: CatalogVisibility
    min_price_enabled: bool
    shop_threshold: Decimal


def require_fabrics(profile: ShopProfile) -> None:
    if not any(spec.code == "fabric" for spec in profile.article_fields):
        msg = "Ce type de boutique ne gère pas de tissus"
        raise ValidationFailed(msg, details={"field": "fabric", "profile": profile.code.value})


def fabric_articles(uow: UnitOfWork, fabric: str) -> list[Article]:
    articles: list[Article] = []
    query = ArticleQuery(fabric=fabric, status=None)
    page = ArticlePageRequest(limit=MAX_LIMIT)
    while True:
        found = ArticleRepository.within(uow).search(query, page)
        articles.extend(a for a in found.items if not a.keys_released)
        if found.next_cursor is None:
            return articles
        page = ArticlePageRequest(limit=MAX_LIMIT, after=found.next_cursor)


@dataclass(frozen=True, slots=True, kw_only=True)
class Author:
    performer: Performer
    user_id: UserId
    now: datetime


def create_colors(
    uow: UnitOfWork,
    context: ShopCatalogContext,
    fabric: str,
    colors: Sequence[str],
    terms: FabricTerms,
    author: Author,
) -> list[Article]:
    articles = ArticleRepository.within(uow)
    created: list[Article] = []
    for color in colors:
        data = ArticleInput(
            fields=color_fields(fabric, color, terms.shape), alert_threshold=terms.alert_threshold
        )
        details = build_details(context.profile, data)
        require_unique(articles, details)
        details = ensure_reference(uow, context.profile, details)
        article = Article.create(uow.shop_id, details, performer=author.performer, now=author.now)
        if terms.prices is not None:
            changes = article.set_prices(
                terms.prices,
                min_price_enabled=context.settings.min_price_enabled,
                performer=author.performer,
                now=author.now,
            )
            record_history(uow, article, changes, author_id=author.user_id, at=author.now)
        articles.add(article)
        created.append(article)
    return created
