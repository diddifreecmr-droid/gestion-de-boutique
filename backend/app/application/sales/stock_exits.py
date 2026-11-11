"""Sorties de stock d'une vente, posées et inversées **par le grand livre** (TR-12, RG-T17).

- `post_exits` : une « Sortie vente » **par article** (somme des lignes du même article,
  ERR-STK-02 : 2 + 1 contrôlés ensemble contre le stock du lieu) au lieu de vente, à l'instant
  de la vente, dans la transaction de la vente. En ligne, un stock insuffisant remonte tel quel
  (`STOCK_INSUFFICIENT` : `article_id`, `available`, `other_locations`) ; en différé (T23) la
  sortie est acceptée et la vente marquée « stock à vérifier » (RG-T18).
- `reverse_exits` : annulation de la vente (UC-VEN-08) → « Annulation » de chaque sortie
  encore en vigueur ; la marchandise revient au lieu de vente.
"""

from datetime import datetime

from app.application.ports.uow import UnitOfWork
from app.application.stock.ledger import StockLedger
from app.application.stock.ports import StockMovementLog
from app.application.stock.postings import Posting
from app.domain.catalog.ids import ArticleId
from app.domain.sales.sale import Sale
from app.domain.shared.ids import UserId
from app.domain.shared.quantity import Quantity
from app.domain.stock.movement import StockMovement
from app.domain.stock.values import MovementType, SourceRef, SourceType


def source_of(sale: Sale) -> SourceRef:
    return SourceRef(SourceType.SALE, sale.id.value, str(sale.number))


def quantities_by_article(sale: Sale) -> dict[ArticleId, Quantity]:
    totals: dict[ArticleId, Quantity] = {}
    for line in sale.content.lines:
        current = totals.get(line.article_id)
        totals[line.article_id] = (
            line.stock_quantity if current is None else current + line.stock_quantity
        )
    return totals


def post_exits(
    uow: UnitOfWork, ledger: StockLedger, sale: Sale, *, deferred: bool
) -> list[StockMovement]:
    movements = [
        ledger.record_exit(
            uow,
            Posting(
                article_id=article_id,
                location_id=sale.location_id,
                type=MovementType.SALE_OUT,
                quantity=quantity,
                source=source_of(sale),
                occurred_at=sale.sold_at,
                author_id=sale.capture.created_by,
            ),
            deferred=deferred,
        )
        for article_id, quantity in quantities_by_article(sale).items()
    ]
    sale.stock_to_verify = any(movement.stock_to_verify for movement in movements)
    return movements


def reverse_exits(
    uow: UnitOfWork, ledger: StockLedger, sale: Sale, *, author_id: UserId, now: datetime
) -> None:
    movements = StockMovementLog.within(uow).for_source(sale.id.value)
    reversed_ids = {m.reverses for m in movements if m.reverses is not None}
    for movement in movements:
        if movement.type is MovementType.SALE_OUT and movement.id not in reversed_ids:
            ledger.reverse(
                uow, movement.id, source=source_of(sale), author_id=author_id, occurred_at=now
            )
