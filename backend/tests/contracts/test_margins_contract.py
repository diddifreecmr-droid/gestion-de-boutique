"""Contrat du port `MarginQueries` (Coûts et marges) : lignes des ventes non annulées par journée
et article, coûts figés, lignes sans coût à part, article introuvable → nom figé de la ligne,
isolation des boutiques. Rejoué sur la mémoire, SQLite et PostgreSQL (`--backend=postgres`).
"""

from decimal import Decimal

from app.application.reporting.margin_ports import MarginQueries
from app.application.sales.ports import SaleRepository
from app.domain.shared.ids import ShopId
from app.domain.shared.quantity import StockUnit
from tests.contracts.backends import ContractBackend
from tests.contracts.helpers import run_in_uow
from tests.contracts.reporting_data import AFTER, BEFORE, D, sales_book


def test_sold_lines_by_day_and_article_without_cancelled_sales(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    book = sales_book(shop_a)

    def add(uow) -> None:  # type: ignore[no-untyped-def]
        for sale in book.sales:
            SaleRepository.within(uow).add(sale)

    run_in_uow(backend, shop_a, add)
    with backend.uow(shop_a) as uow:
        rows = MarginQueries.within(uow).sold_by_article(BEFORE, AFTER)
    assert {r.day for r in rows} == {D}  # s3 (veille) et s4 annulées : exclues
    assert {(r.name, r.stock_unit, r.fabric, r.roll_length_m) for r in rows} == {
        ("Haojue HJ125-8", StockUnit.UNIT, None, None)
    }
    sums = sorted((r.revenue, r.costed_revenue, r.cost, r.without_cost) for r in rows)
    assert sums == [(100_000, 0, 0, 1), (700_000, 700_000, 550_000, 0),
                    (780_000, 780_000, 550_000, 0)]  # fmt: skip
    assert {(r.quantity, r.costed_quantity) for r in rows} == {
        (Decimal(1), Decimal(0)),
        (Decimal(1), Decimal(1)),
    }
    with backend.uow(shop_b) as uow:
        assert MarginQueries.within(uow).sold_by_article(BEFORE, AFTER) == []
