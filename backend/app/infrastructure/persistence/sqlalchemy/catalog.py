"""Dépôts SQL du catalogue (T13) : `article` (gabarit `SqlRepository`) et `price_history`.

La recherche filtre sur `search_key LIKE '%terme%'` : clé et terme sont déjà pliés par le
domaine (minuscules, sans accent ni ponctuation), donc la requête est portable et le terme ne
contient aucun caractère spécial de `LIKE`. Ordre et curseur sur `(sort_key, id)`.
"""

from decimal import Decimal
from typing import Any

import sqlalchemy as sa

from app.application.catalog.ports import (
    ARTICLE_BRAND_MODEL,
    ARTICLE_REFERENCE,
    ArticleRepository,
    PriceHistoryLog,
)
from app.application.catalog.search import ArticlePage, ArticlePageRequest, ArticleQuery, page_of
from app.domain.catalog.article import Article
from app.domain.catalog.details import ArticleDetails, ArticleStatus
from app.domain.catalog.ids import ArticleId, AttachmentId, PriceHistoryId
from app.domain.catalog.prices import ArticlePrices, PriceHistory, PriceKind
from app.domain.catalog.schema import ProfileFields
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shared.quantity import StockUnit
from app.infrastructure.persistence.errors import PRIMARY_KEY, duplicate
from app.infrastructure.persistence.sqlalchemy import tables_catalog as t
from app.infrastructure.persistence.sqlalchemy.columns import from_db, to_db
from app.infrastructure.persistence.sqlalchemy.shop_store import SqlShopStore
from app.infrastructure.persistence.sqlalchemy.shops import SqlListing

_KEY_COLUMNS = {ARTICLE_BRAND_MODEL: "brand_model_key", ARTICLE_REFERENCE: "reference_key"}


def _amount(value: Money | None) -> int | None:
    return None if value is None else value.amount


def _money(value: object) -> Money | None:
    return None if value is None else Money(int(str(value)))


def _decimal(value: object) -> Decimal | None:
    return None if value is None else Decimal(str(value))


class SqlArticleRepository(SqlListing[ArticleId, Article], ArticleRepository):
    table = t.article

    def _to_columns(self, aggregate: Article) -> dict[str, Any]:
        details, fields, prices = aggregate.details, aggregate.details.fields, aggregate.prices
        return {
            "display_name": fields.display_name,
            "brand": fields.brand,
            "model": fields.model,
            "reference": fields.reference,
            "brand_model_key": details.brand_model_key,
            "reference_key": details.reference_key,
            "search_key": details.search_key,
            "sort_key": details.sort_key,
            "stock_unit": fields.stock_unit.value,
            "sold_by_piece": fields.sold_by_piece,
            "piece_length_m": fields.piece_length_m,
            "alert_threshold": details.alert_threshold,
            "photo_id": None if details.photo_id is None else details.photo_id.value,
            "notes": details.notes,
            "attributes": dict(fields.attributes),
            **{kind.value: _amount(prices.of(kind)) for kind in PriceKind},
            "last_cost": _amount(aggregate.last_cost),
            "wac": _amount(aggregate.wac),
            "status": aggregate.status.value,
            "created_at": to_db(aggregate.created_at),
        }

    def _from_row(self, row: sa.RowMapping) -> Article:
        fields = ProfileFields(
            display_name=row["display_name"],
            brand=row["brand"],
            model=row["model"],
            reference=row["reference"],
            stock_unit=StockUnit(row["stock_unit"]),
            sold_by_piece=bool(row["sold_by_piece"]),
            piece_length_m=_decimal(row["piece_length_m"]),
            attributes=dict(row["attributes"]),
        )
        photo = row["photo_id"]
        details = ArticleDetails(
            fields=fields,
            alert_threshold=_decimal(row["alert_threshold"]),
            photo_id=None if photo is None else AttachmentId(photo),
            notes=row["notes"],
        )
        return Article(
            id=ArticleId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            details=details,
            created_at=from_db(row["created_at"]),
            prices=ArticlePrices(**{kind.value: _money(row[kind.value]) for kind in PriceKind}),
            status=ArticleStatus(row["status"]),
            last_cost=_money(row["last_cost"]),
            wac=_money(row["wac"]),
            version=int(row["version"]),
        )

    def find_by_key(self, constraint: str, key: str) -> Article | None:
        column = self.table.c[_KEY_COLUMNS[constraint]]
        found = self._select_all(self.table.c.id, where=column == key)
        return found[0] if found else None

    def search(self, query: ArticleQuery, page: ArticlePageRequest) -> ArticlePage:
        c = self.table.c
        conditions: list[sa.ColumnElement[bool]] = []
        if query.status is not None:
            conditions.append(c.status == query.status.value)
        text = query.folded_text
        if text is not None:
            conditions.append(c.search_key.like(f"%{text}%"))
        after = page.after
        if after is not None:
            conditions.append(
                sa.or_(
                    c.sort_key > after.sort_key,
                    sa.and_(c.sort_key == after.sort_key, c.id > after.id),
                )
            )
        statement = (
            sa.select(self.table)
            .where(c.shop_id == self.shop_id.value, *conditions)
            .order_by(c.sort_key, c.id)
            .limit(page.limit + 1)
        )
        articles = [self._from_row(row) for row in self._transaction.fetch_all(statement)]
        for article in articles:
            self._tracker.track(article, saved=False)
        return page_of(articles, page)


class SqlPriceHistoryLog(SqlShopStore, PriceHistoryLog):
    table = t.price_history

    def _append(self, entry: PriceHistory) -> None:
        values = {
            "id": entry.id.value,
            "shop_id": entry.shop_id.value,
            "article_id": entry.article_id.value,
            "price_kind": entry.kind.value,
            "old_price": _amount(entry.old_price),
            "new_price": _amount(entry.new_price),
            "effective_at": to_db(entry.effective_at),
            "author_id": entry.author_id.value,
        }
        try:
            self._transaction.write(sa.insert(self.table).values(values))
        except sa.exc.IntegrityError as exc:
            taken = sa.select(self.table.c.id).where(self.table.c.id == entry.id.value)
            if not self._transaction.exists(taken):
                raise  # contrainte imprévue : l'erreur remonte telle quelle (fail-fast)
            raise duplicate(self.table.name, PRIMARY_KEY) from exc

    def for_article(self, article_id: ArticleId) -> list[PriceHistory]:
        c = self.table.c
        statement = (
            sa.select(self.table)
            .where(self._own_shop(), c.article_id == article_id.value)
            .order_by(c.effective_at.desc(), c.id.desc())
        )
        return [
            PriceHistory(
                id=PriceHistoryId(row["id"]),
                shop_id=ShopId(row["shop_id"]),
                article_id=ArticleId(row["article_id"]),
                kind=PriceKind(row["price_kind"]),
                old_price=_money(row["old_price"]),
                new_price=_money(row["new_price"]),
                effective_at=from_db(row["effective_at"]),
                author_id=UserId(row["author_id"]),
            )
            for row in self._transaction.fetch_all(statement)
        ]


SQL_CATALOG_REPOSITORIES = (SqlArticleRepository, SqlPriceHistoryLog)
