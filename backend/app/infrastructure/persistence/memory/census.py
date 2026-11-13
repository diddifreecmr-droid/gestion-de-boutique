"""Adaptateur mémoire de `ShopDataCensus` (T27) : lignes visibles de la boutique par table.

Les noms de table sont ceux des dépôts mémoire des modules (`catalog.py`, `stock.py`,
`sales.py`, `purchasing.py`, `expenses.py`, `receivables.py`) ; le contrat partagé avec
l'adaptateur SQL prouve que chaque nature est bien comptée.
"""

from collections.abc import Mapping
from types import MappingProxyType

from app.application.shops.census import ShopDataCensus
from app.domain.shops.profile_change import DATA_KINDS, BlockingKind
from app.infrastructure.persistence.memory.shop_store import MemoryShopStore

TABLES: Mapping[BlockingKind, str] = MappingProxyType(
    {
        BlockingKind.ARTICLES: "articles",
        BlockingKind.MOVEMENTS: "stock_movements",
        BlockingKind.SALES: "sales",
        BlockingKind.PURCHASES: "purchases",
        BlockingKind.EXPENSES: "expenses",
        BlockingKind.RECEIVABLES: "receivables",
    }
)
if set(TABLES) != set(DATA_KINDS):  # une nature ajoutée sans table échoue à l'import
    _msg = f"memory/census.py : natures sans table {sorted(set(DATA_KINDS) - set(TABLES))}"
    raise RuntimeError(_msg)


class MemoryShopDataCensus(MemoryShopStore, ShopDataCensus):
    table = "articles"

    def counts(self) -> Mapping[BlockingKind, int]:
        return {kind: len(self._transaction.rows(TABLES[kind])) for kind in DATA_KINDS}
