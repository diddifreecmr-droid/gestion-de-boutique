"""UC-VEN-08 — Annuler une vente (propriétaire seul, `SALE_CANCEL` ; recette SCN-06).

Motif obligatoire (400). Dans une transaction : la vente est barrée (« Annulée le … par … —
motif : … », elle garde son numéro, RG-T05), chaque « Sortie vente » est inversée par une
« Annulation » (la marchandise revient au lieu de vente), ses châssis redeviennent libres
(RG-M01, SCN-06 étape 8) et, pour une vente à crédit, `CreditSaleCancelled` dit à T17 d'annuler
la créance liée (`refund_payments` : ses versements deviennent « à rembourser »). Annuler une
seconde fois → `INVALID_STATE_TRANSITION`. Journal « sensible ». Dans les totaux, l'annulation
compte **le jour où elle est faite** (Q-09). Une vente qui a un retour ne s'annule plus
(`INVALID_STATE_TRANSITION`, T16b : ses retours restent la référence).
"""

from dataclasses import dataclass

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.sales.chassis_claims import release_claims
from app.application.sales.ports import SaleRepository
from app.application.sales.retry import with_sale_retry
from app.application.sales.returning import require_no_returns
from app.application.sales.stock_exits import reverse_exits
from app.application.sales.views import SaleView, view_of
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of
from app.application.stock.ledger import StockLedger
from app.domain.sales.ids import SaleId


@dataclass(frozen=True, slots=True, kw_only=True)
class CancelSaleCommand:
    sale_id: SaleId
    reason: str
    refund_payments: bool = False


class CancelSale:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, policy: Policy, ledger: StockLedger, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._ledger = ledger
        self._clock = clock

    def execute(self, actor: Actor, command: CancelSaleCommand) -> SaleView:
        self._policy.require(actor, Permission.SALE_CANCEL)  # avant toute lecture
        return with_sale_retry(lambda: self._attempt(actor, command))

    def _attempt(self, actor: Actor, command: CancelSaleCommand) -> SaleView:
        now = self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            sales = SaleRepository.within(uow)
            sale = sales.get(command.sale_id)
            require_no_returns(uow, sale)
            sale.cancel(
                command.reason,
                refund_payments=command.refund_payments,
                performer=performer_of(actor),
                now=now,
            )
            sales.update(sale)
            reverse_exits(uow, self._ledger, sale, author_id=actor.user_id, now=now)
            release_claims(uow, sale)
            uow.commit()
        return view_of(self._policy, actor, sale)
