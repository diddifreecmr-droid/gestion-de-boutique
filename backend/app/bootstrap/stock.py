"""Assemblage du module Stock (T14) : grand livre, ajustements, inventaires, lectures.

- Un seul `StockLedger` par application : les modules Achats (T15), Ventes (T16) et
  Déplacements (Lot 2) le reçoivent de `StockModule.ledger` pour poster leurs mouvements dans
  leur propre transaction.
- Les règles d'alerte du stock sont branchées par le noyau (`bootstrap/core.py`), une fois.
- Les ports `ArticleStock` / `LocationStock` (archivage d'article, désactivation de lieu) sont
  servis par `application/stock/probes.py`, branchés par `bootstrap/catalog.py` et `shops.py`.
"""

from dataclasses import dataclass

from app.application.security.policy import Policy
from app.application.stock.ledger import StockLedger
from app.application.stock.use_cases.inventories import GetInventory, StartInventory
from app.application.stock.use_cases.inventory_counts import AbandonInventory, RecordCounts
from app.application.stock.use_cases.inventory_validate import ValidateInventory
from app.application.stock.use_cases.record_adjustment import RecordAdjustment
from app.application.stock.use_cases.stock_history import ReadArticleMovements, ReadDamagedStock
from app.application.stock.use_cases.stock_matrix import ReadStockMatrix
from app.application.stock.use_cases.stock_value import ReadStockValue
from app.bootstrap.identity import IdentityModule
from app.interface.http.routes.stock_components import StockComponents


@dataclass(frozen=True, slots=True, kw_only=True)
class StockModule:
    ledger: StockLedger
    http: StockComponents


def build_stock(identity: IdentityModule) -> StockModule:
    uows, clock = identity.core.shop_uow_factory, identity.clock
    policy = Policy(clock=clock.now)
    ledger = StockLedger(clock)
    http = StockComponents(
        matrix=ReadStockMatrix(uows, policy),
        value=ReadStockValue(uows, policy),
        damaged=ReadDamagedStock(uows, policy),
        movements=ReadArticleMovements(uows, policy),
        adjust=RecordAdjustment(uows, policy, ledger, clock),
        start_inventory=StartInventory(uows, policy, clock),
        get_inventory=GetInventory(uows, policy),
        counts=RecordCounts(uows, policy, clock),
        validate_inventory=ValidateInventory(uows, policy, ledger, clock),
        abandon_inventory=AbandonInventory(uows, policy, clock),
        guard=identity.auth.guard,
    )
    return StockModule(ledger=ledger, http=http)
