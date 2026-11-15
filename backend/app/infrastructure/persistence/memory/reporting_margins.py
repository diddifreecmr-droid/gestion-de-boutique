"""Adaptateur mémoire du port `MarginQueries` (Coûts et marges) : lit les ventes et les articles de
la transaction, sans les suivre (lecture seule). Sémantique décrite dans
`application/reporting/margin_ports.py`, vérifiée par `tests/contracts/test_margins_contract.py`.
"""

import copy
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import cast

from app.application.reporting.margin_ports import ArticleDaySales, MarginQueries
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId
from app.domain.sales.lines import SaleLine
from app.domain.sales.sale import Sale
from app.infrastructure.persistence.memory.shop_store import MemoryShopStore


def _row(day: date, lines: list[SaleLine], article: Article | None) -> ArticleDaySales:
    costed = [line for line in lines if line.margin is not None]
    revenue = sum(line.line_total.amount for line in costed)
    first = lines[0]
    fields = None if article is None else article.details.fields
    return ArticleDaySales(
        day=day,
        article_id=first.article_id,
        name=first.article_name if article is None else article.display_name,
        fabric=None if fields is None else fields.fabric,
        stock_unit=first.stock_quantity.unit if fields is None else fields.stock_unit,
        roll_length_m=None if fields is None else fields.piece_length_m,
        quantity=sum((line.stock_quantity.value for line in lines), Decimal(0)),
        costed_quantity=sum((line.stock_quantity.value for line in costed), Decimal(0)),
        revenue=sum(line.line_total.amount for line in lines),
        costed_revenue=revenue,
        cost=revenue - sum(m.amount for line in costed if (m := line.margin) is not None),
        without_cost=len(lines) - len(costed),
    )


class MemoryMarginQueries(MemoryShopStore, MarginQueries):
    table = "sales"

    def sold_by_article(self, first_day: date, last_day: date) -> list[ArticleDaySales]:
        groups: dict[tuple[date, ArticleId], list[SaleLine]] = defaultdict(list)
        for row in self._transaction.rows("sales"):
            sale = cast(Sale, copy.deepcopy(row.payload))
            day = sale.content.sold_on
            if sale.cancellation is None and first_day <= day <= last_day:
                for line in sale.content.lines:
                    groups[(day, line.article_id)].append(line)
        articles = {
            article.id: article
            for row in self._transaction.rows("articles")
            if isinstance(article := row.payload, Article)
        }
        return [
            _row(day, lines, articles.get(article_id))
            for (day, article_id), lines in sorted(
                groups.items(), key=lambda g: (g[0][0], str(g[0][1].value))
            )
        ]


MEMORY_MARGIN_ADAPTERS = (MemoryMarginQueries,)
