"""Contrat du port `ShopDataCensus` (T27, QC-1) : chaque nature est comptée, dans la transaction,
pour la seule boutique de l'unité de travail.

Rejoué sur l'adaptateur mémoire, sur SQLite (`tests/infrastructure/sqlalchemy`) et sur
PostgreSQL (`--backend=postgres`).
"""

from app.application.expenses.ports import ExpenseRepository
from app.application.purchasing.ports import PurchaseRepository
from app.application.receivables.ports import ReceivableRepository
from app.application.sales.ports import SaleRepository
from app.application.shops.census import ShopDataCensus
from app.application.stock.ports import StockMovementLog
from app.domain.shared.ids import ShopId
from app.domain.shops.profile_change import DATA_KINDS, BlockingKind
from tests.contracts.backends import ContractBackend
from tests.contracts.expense_data import expense
from tests.contracts.purchasing_data import purchase
from tests.contracts.receivables_data import receivable
from tests.contracts.sales_data import sale
from tests.contracts.stock_data import movement, seed


def test_an_empty_shop_counts_zero_everywhere(backend: ContractBackend, shop_a: ShopId) -> None:
    with backend.uow(shop_a) as uow:
        assert ShopDataCensus.within(uow).counts() == dict.fromkeys(DATA_KINDS, 0)


def test_each_kind_is_counted_for_its_shop_only(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    data = seed(backend, shop_a)  # boutique, réglages, deux lieux, un article
    seed(backend, shop_b)
    with backend.uow(shop_a) as uow:
        opening = movement(shop_a, data.article.id, data.garoua.id)
        StockMovementLog.within(uow).append(opening)
        SaleRepository.within(uow).add(sale(shop_a, 1))
        SaleRepository.within(uow).add(sale(shop_a, 2, chassis="LBX124"))
        PurchaseRepository.within(uow).add(purchase(shop_a, 1, location_id=data.garoua.id))
        ExpenseRepository.within(uow).add(expense(shop_a, 1))
        ReceivableRepository.within(uow).add(receivable(shop_a))
        expected = {
            BlockingKind.ARTICLES: 1,
            BlockingKind.MOVEMENTS: 1,
            BlockingKind.SALES: 2,
            BlockingKind.PURCHASES: 1,
            BlockingKind.EXPENSES: 1,
            BlockingKind.RECEIVABLES: 1,
        }
        assert ShopDataCensus.within(uow).counts() == expected  # écritures non validées vues
        uow.commit()
    with backend.uow(shop_a) as uow:
        assert ShopDataCensus.within(uow).counts() == expected
    with backend.uow(shop_b) as uow:
        assert ShopDataCensus.within(uow).counts() == {
            **dict.fromkeys(DATA_KINDS, 0),
            BlockingKind.ARTICLES: 1,
        }
