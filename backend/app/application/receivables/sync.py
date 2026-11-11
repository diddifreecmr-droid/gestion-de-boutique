"""Handler `ReceivableSync` : la créance suit sa vente, **dans la transaction de la vente**.

Branché sur les unités de travail de boutique (`bootstrap/core.py`), il consomme les
événements de `domain/sales/receivable_events.py` :

| Événement | Effet |
| --- | --- |
| `CreditSaleRecorded` | ouvre la créance (UC-CRE-01) ; un échec annule la vente |
| `CreditSaleAmountsChanged` | nouveau montant initial (`AMOUNT_BELOW_PAID` si < versé) |
| `CreditSaleCancelled` | créance Annulée, versements « à rembourser » si demandé (Q-09) |
| `CreditSaleReturned` | baisse du montant initial, plafonnée au reste réel (T16b) |

Une créance absente pour une vente à crédit est une incohérence : `NotFound` remonte et
annule la transaction (jamais ignorée).
"""

from app.application.ports.event_handler import EventHandler
from app.application.ports.uow import UnitOfWork
from app.application.receivables.ports import ReceivableRepository
from app.application.sales.ports import SaleRepository
from app.domain.receivables.ids import receivable_id_for_sale
from app.domain.receivables.receivable import Receivable
from app.domain.sales.ids import SaleId
from app.domain.sales.receivable_events import (
    CreditSaleAmountsChanged,
    CreditSaleCancelled,
    CreditSaleRecorded,
    CreditSaleReturned,
)
from app.domain.shared.business_day import business_date
from app.domain.shared.events import DomainEvent


class ReceivableSync(EventHandler):
    def handle(self, event: DomainEvent, uow: UnitOfWork) -> None:
        if isinstance(event, CreditSaleRecorded):
            sale = SaleRepository.within(uow).get(event.sale_id)
            receivable = Receivable.open_from_sale(event, total=sale.total)
            ReceivableRepository.within(uow).add(receivable)
            return
        if isinstance(event, CreditSaleAmountsChanged):
            receivable = self._linked(uow, event.sale_id)
            receivable.revise_from_sale(
                customer_id=event.customer_id,
                total=event.total,
                paid_at_sale=event.paid_at_sale,
                initial=event.initial_amount,
            )
        elif isinstance(event, CreditSaleCancelled):
            receivable = self._linked(uow, event.sale_id)
            receivable.cancel_by_sale(
                refund_payments=event.refund_payments,
                on=business_date(event.occurred_at),
                at=event.occurred_at,
            )
        elif isinstance(event, CreditSaleReturned):
            receivable = self._linked(uow, event.sale_id)
            receivable.reduce_by_return(event.amount)
        else:
            return
        ReceivableRepository.within(uow).update(receivable)

    @staticmethod
    def _linked(uow: UnitOfWork, sale_id: SaleId) -> Receivable:
        return ReceivableRepository.within(uow).get(receivable_id_for_sale(sale_id))
