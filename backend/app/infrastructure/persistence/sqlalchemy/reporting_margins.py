"""Adaptateur SQL du port `MarginQueries` (Coûts et marges, specs § 15.1).

Une requête bornée par l'index `sale (shop_id, sold_on)` : lignes des ventes non annulées
(`cancelled_at` nul) groupées par journée et article ; puis les articles concernés (clé primaire)
pour le nom, le tissu, l'unité et la longueur du rouleau. Coût = Σ (montant - marge) des lignes
dont la marge au dernier coût figé est connue. SQL portable (PostgreSQL et SQLite).
"""

from datetime import date
from decimal import Decimal
from typing import Any

import sqlalchemy as sa

from app.application.reporting.margin_ports import ArticleDaySales, MarginQueries
from app.domain.catalog.ids import ArticleId
from app.domain.shared.quantity import StockUnit
from app.infrastructure.persistence.sqlalchemy import tables_catalog as c
from app.infrastructure.persistence.sqlalchemy import tables_sales as t
from app.infrastructure.persistence.sqlalchemy.reporting_sales import null_count, total
from app.infrastructure.persistence.sqlalchemy.shop_store import SqlShopStore

S, L, A = t.sale.c, t.sale_line.c, c.article.c
_LINES = t.sale.join(t.sale_line, sa.and_(L.sale_id == S.id, L.shop_id == S.shop_id))


def _costed(column: sa.ColumnElement[Any]) -> sa.ColumnElement[Any]:
    return total(sa.case((L.margin.is_not(None), column), else_=0))


class SqlMarginQueries(SqlShopStore, MarginQueries):
    table = t.sale

    def sold_by_article(self, first_day: date, last_day: date) -> list[ArticleDaySales]:
        statement = (
            sa.select(
                S.sold_on,
                L.article_id,
                sa.func.max(L.article_name_snapshot).label("name"),
                sa.func.max(L.stock_unit).label("unit"),
                total(L.stock_qty).label("quantity"),
                _costed(L.stock_qty).label("costed_quantity"),
                total(L.line_total).label("revenue"),
                _costed(L.line_total).label("costed_revenue"),
                total(L.margin).label("margin"),
                null_count(L.margin).label("without_cost"),
            )
            .select_from(_LINES)
            .where(S.shop_id == self.shop_id.value, S.sold_on >= first_day)
            .where(S.sold_on <= last_day, S.cancelled_at.is_(None))
            .group_by(S.sold_on, L.article_id)
        )
        rows = self._transaction.fetch_all(statement)
        articles = self._articles({row["article_id"] for row in rows})
        found = [self._row(row, articles.get(row["article_id"])) for row in rows]
        return sorted(found, key=lambda r: (r.day, str(r.article_id.value)))

    def _articles(self, ids: set[Any]) -> dict[Any, Any]:
        if not ids:
            return {}
        statement = sa.select(A.id, A.display_name, A.fabric, A.stock_unit, A.piece_length_m).where(
            A.shop_id == self.shop_id.value, A.id.in_(ids)
        )
        return {row["id"]: row for row in self._transaction.fetch_all(statement)}

    @staticmethod
    def _row(row: Any, article: Any) -> ArticleDaySales:
        costed = int(row["costed_revenue"])
        length = None if article is None else article["piece_length_m"]
        return ArticleDaySales(
            day=row["sold_on"],
            article_id=ArticleId(row["article_id"]),
            name=row["name"] if article is None else article["display_name"],
            fabric=None if article is None else article["fabric"],
            stock_unit=StockUnit(row["unit"] if article is None else article["stock_unit"]),
            roll_length_m=None if length is None else Decimal(str(length)),
            quantity=Decimal(str(row["quantity"])),
            costed_quantity=Decimal(str(row["costed_quantity"])),
            revenue=int(row["revenue"]),
            costed_revenue=costed,
            cost=costed - int(row["margin"]),
            without_cost=int(row["without_cost"]),
        )


SQL_MARGIN_ADAPTERS = (SqlMarginQueries,)
"""Adaptateur SQL des Coûts et marges, à inscrire dans `SQL_REPOSITORIES`."""
