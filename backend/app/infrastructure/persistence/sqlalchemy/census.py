"""Adaptateur SQL de `ShopDataCensus` (T27) : un `count(*)` par table, filtré sur la boutique.

Chaque table a un index qui commence par `shop_id` : le comptage reste bon marché. Aucune
table ni colonne n'est ajoutée (aucune migration).
"""

from collections.abc import Mapping
from types import MappingProxyType

import sqlalchemy as sa

from app.application.shops.census import ShopDataCensus
from app.domain.shops.profile_change import DATA_KINDS, BlockingKind
from app.infrastructure.persistence.sqlalchemy.shop_store import SqlShopStore
from app.infrastructure.persistence.sqlalchemy.tables_catalog import article
from app.infrastructure.persistence.sqlalchemy.tables_expenses import expense
from app.infrastructure.persistence.sqlalchemy.tables_purchasing import purchase
from app.infrastructure.persistence.sqlalchemy.tables_receivables import receivable
from app.infrastructure.persistence.sqlalchemy.tables_sales import sale
from app.infrastructure.persistence.sqlalchemy.tables_stock import stock_movement

TABLES: Mapping[BlockingKind, sa.Table] = MappingProxyType(
    {
        BlockingKind.ARTICLES: article,
        BlockingKind.MOVEMENTS: stock_movement,
        BlockingKind.SALES: sale,
        BlockingKind.PURCHASES: purchase,
        BlockingKind.EXPENSES: expense,
        BlockingKind.RECEIVABLES: receivable,
    }
)
if set(TABLES) != set(DATA_KINDS):  # une nature ajoutée sans table échoue à l'import
    _msg = f"sqlalchemy/census.py : natures sans table {sorted(set(DATA_KINDS) - set(TABLES))}"
    raise RuntimeError(_msg)


class SqlShopDataCensus(SqlShopStore, ShopDataCensus):
    table = article

    def counts(self) -> Mapping[BlockingKind, int]:
        return {kind: self._count(TABLES[kind]) for kind in DATA_KINDS}

    def _count(self, table: sa.Table) -> int:
        statement = (
            sa.select(sa.func.count().label("n"))
            .select_from(table)
            .where(table.c.shop_id == self.shop_id.value)
        )
        row = self._transaction.fetch_one(statement)
        if row is None:  # un count(*) renvoie toujours une ligne : défense en profondeur
            msg = f"count(*) sans ligne sur {table.name}"
            raise RuntimeError(msg)
        return int(row["n"])
