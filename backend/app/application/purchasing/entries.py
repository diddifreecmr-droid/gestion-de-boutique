"""Mouvements « Entrée achat » d'un achat, posés et inversés **par le grand livre** (TR-12).

- `post_entries` : une entrée par ligne au lieu de réception, quantité de stock (RG-X02), coût
  unitaire final (RG-T10), date de l'opération = `Purchase.entry_instant` (date d'achat).
- `live_entries` : entrées de l'achat encore en vigueur (non annulées).
- `quantity_left` (décision Q-07, contrôle **par article x lieu**, le stock n'est pas suivi par
  lot) : part d'une entrée qui a déjà quitté le lieu = `quantité - plus bas solde du lieu
  depuis l'entrée` (bornée à 0). Retirer l'entrée rendrait ce solde négatif d'autant : ces
  unités sont donc vendues, déplacées ou sorties. PUR-06 : 10 reçues, 8 vendues → 8 sorties.
- `require_kept` : refuse (`StockAlreadyLeft`) une correction qui garderait moins que la part
  sortie, ou une annulation (on ne garde rien) dès qu'une unité est sortie (UC-ACH-03/04).
- `reverse_entries` : « Annulation » de chaque entrée, à l'instant de la correction.

Ordre d'une correction : contrôle, **nouvelles** entrées, puis annulation des anciennes — le
solde du lieu ne passe jamais sous zéro en cours de route (la règle en ligne du grand livre).
"""

from collections.abc import Iterable, Mapping
from datetime import datetime

from app.application.ports.uow import UnitOfWork
from app.application.stock.ledger import StockLedger
from app.application.stock.ports import StockMovementLog
from app.application.stock.postings import Posting
from app.domain.catalog.ids import ArticleId
from app.domain.purchasing.errors import StockAlreadyLeft
from app.domain.purchasing.ids import PurchaseId
from app.domain.purchasing.purchase import Purchase
from app.domain.shared.ids import UserId
from app.domain.shared.quantity import Quantity
from app.domain.shops.ids import LocationId
from app.domain.stock.movement import StockMovement
from app.domain.stock.values import MovementType, SourceRef, SourceType

type Kept = Mapping[tuple[ArticleId, LocationId], Quantity]


def source_of(purchase: Purchase) -> SourceRef:
    return SourceRef(SourceType.PURCHASE, purchase.id.value, str(purchase.number))


def post_entries(
    uow: UnitOfWork, ledger: StockLedger, purchase: Purchase, author_id: UserId
) -> list[StockMovement]:
    return [
        ledger.record_entry(
            uow,
            Posting(
                article_id=line.line.article_id,
                location_id=purchase.details.location_id,
                type=MovementType.PURCHASE_IN,
                quantity=line.stock_quantity,
                source=source_of(purchase),
                occurred_at=purchase.entry_instant,
                author_id=author_id,
                unit_cost=line.unit_cost,
            ),
        )
        for line in purchase.costed
    ]


def live_entries(uow: UnitOfWork, purchase_id: PurchaseId) -> list[StockMovement]:
    movements = StockMovementLog.within(uow).for_source(purchase_id.value)
    reversed_ids = {m.reverses for m in movements if m.reverses is not None}
    return [m for m in movements if m.type is MovementType.PURCHASE_IN and m.id not in reversed_ids]


def quantity_left(uow: UnitOfWork, entry: StockMovement) -> Quantity:
    history = StockMovementLog.within(uow).chronology(entry.article_id)
    since = [
        m.balance_after
        for m in history
        if m.location_id == entry.location_id
        and m.condition is entry.condition
        and m.id >= entry.id
    ]
    if not since:
        msg = f"Entrée {entry.id} absente du grand livre de son article"
        raise RuntimeError(msg)
    left = entry.quantity - min(since)
    return left if left.value > 0 else Quantity.zero(left.unit)


def require_kept(uow: UnitOfWork, entries: Iterable[StockMovement], kept: Kept) -> None:
    for entry in entries:
        left = quantity_left(uow, entry)
        keep = kept.get((entry.article_id, entry.location_id), Quantity.zero(left.unit))
        if left > keep:
            raise StockAlreadyLeft(
                article_id=str(entry.article_id),
                location_id=str(entry.location_id),
                left=left,
                requested=keep,
            )


def reverse_entries(
    uow: UnitOfWork,
    ledger: StockLedger,
    purchase: Purchase,
    entries: Iterable[StockMovement],
    *,
    author_id: UserId,
    now: datetime,
) -> None:
    for entry in entries:
        ledger.reverse(
            uow, entry.id, source=source_of(purchase), author_id=author_id, occurred_at=now
        )
