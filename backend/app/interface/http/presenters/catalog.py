"""Présentation du catalogue **selon le rôle** (TR-05, RG-D02, SEC-N01, SEC-N02).

Un champ invisible n'est **pas posé** sur la réponse : la route le retire à la sérialisation
(`response_model_exclude_unset`), la clé n'existe donc pas dans le JSON. La décision « qui voit
quoi » vient de `CatalogVisibility` (application) ; ce module n'en prend aucune.
"""

from decimal import Decimal
from typing import Any

from app.application.catalog.use_cases.read_articles import ArticleList, ArticleSheet
from app.application.catalog.visibility import CatalogVisibility
from app.domain.catalog.article import Article
from app.domain.catalog.prices import MINIMUM_KINDS, PriceHistory, PriceKind
from app.interface.http.schemas.catalog import (
    ArticleListResponse,
    ArticleResponse,
    PriceHistoryResponse,
)


def _optional(value: object) -> str | None:
    return None if value is None else str(value)


def _restricted(
    article: Article, visibility: CatalogVisibility, *, min_price_enabled: bool
) -> dict[str, Any]:
    values: dict[str, Any] = {}
    prices = article.prices
    if visibility.selling_prices:
        for kind in PriceKind:
            if kind not in MINIMUM_KINDS or visibility.min_prices:
                price = prices.of(kind)
                values[kind.value] = None if price is None else price.amount
    if visibility.min_prices:
        values["min_price_active"] = min_price_enabled
    if visibility.costs:
        values["last_cost"] = None if article.last_cost is None else article.last_cost.amount
        values["wac"] = None if article.wac is None else article.wac.amount
    return values


def article_response(
    article: Article,
    visibility: CatalogVisibility,
    *,
    min_price_enabled: bool,
    shop_threshold: Decimal,
    history: list[PriceHistory] | None = None,
) -> ArticleResponse:
    details, fields = article.details, article.details.fields
    extra = _restricted(article, visibility, min_price_enabled=min_price_enabled)
    if history is not None and visibility.price_history:
        extra["price_history"] = [history_response(entry) for entry in history]
    return ArticleResponse(
        id=str(article.id),
        version=article.version,
        status=article.status.value,
        display_name=fields.display_name,
        brand=fields.brand,
        model=fields.model,
        reference=fields.reference,
        stock_unit=fields.stock_unit.value,
        sold_by_piece=fields.sold_by_piece,
        piece_length_m=_optional(fields.piece_length_m),
        attributes=dict(fields.attributes),
        alert_threshold=_optional(details.alert_threshold),
        effective_alert_threshold=str(details.effective_threshold(shop_threshold)),
        photo_id=_optional(details.photo_id),
        notes=details.notes,
        created_at=article.created_at,
        **extra,
    )


def history_response(entry: PriceHistory) -> PriceHistoryResponse:
    return PriceHistoryResponse(
        price_kind=entry.kind.value,
        old_price=None if entry.old_price is None else entry.old_price.amount,
        new_price=None if entry.new_price is None else entry.new_price.amount,
        effective_at=entry.effective_at,
        author_id=str(entry.author_id),
    )


def sheet_response(sheet: ArticleSheet) -> ArticleResponse:
    return article_response(
        sheet.article,
        sheet.visibility,
        min_price_enabled=sheet.min_price_enabled,
        shop_threshold=sheet.shop_threshold,
        history=sheet.price_history,
    )


def list_response(found: ArticleList) -> ArticleListResponse:
    cursor = found.page.next_cursor
    return ArticleListResponse(
        items=[
            article_response(
                article,
                found.visibility,
                min_price_enabled=found.min_price_enabled,
                shop_threshold=found.shop_threshold,
            )
            for article in found.page.items
        ],
        next_cursor=None if cursor is None else cursor.encode(),
    )
