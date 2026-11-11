"""Dépendances des routes du stock (assemblées par `bootstrap/stock.py`)."""

from dataclasses import dataclass

from app.application.stock.use_cases.inventories import GetInventory, StartInventory
from app.application.stock.use_cases.inventory_counts import AbandonInventory, RecordCounts
from app.application.stock.use_cases.inventory_validate import ValidateInventory
from app.application.stock.use_cases.record_adjustment import RecordAdjustment
from app.application.stock.use_cases.stock_history import ReadArticleMovements, ReadDamagedStock
from app.application.stock.use_cases.stock_matrix import ReadStockMatrix
from app.application.stock.use_cases.stock_value import ReadStockValue
from app.interface.http.security import AuthGuard


@dataclass(frozen=True, slots=True, kw_only=True)
class StockComponents:
    matrix: ReadStockMatrix
    value: ReadStockValue
    damaged: ReadDamagedStock
    movements: ReadArticleMovements
    adjust: RecordAdjustment
    start_inventory: StartInventory
    get_inventory: GetInventory
    counts: RecordCounts
    validate_inventory: ValidateInventory
    abandon_inventory: AbandonInventory
    guard: AuthGuard
