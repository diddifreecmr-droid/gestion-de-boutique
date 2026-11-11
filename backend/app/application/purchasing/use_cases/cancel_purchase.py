"""UC-ACH-04 — Annuler un achat (propriétaire seul, `PURCHASE_CANCEL` ; recette PUR-09, PUR-10).

Motif obligatoire. Refus (`STOCK_ALREADY_LEFT`, 422) si une partie de la marchandise a déjà
quitté le lieu de réception (vendue, déplacée, sortie : `require_kept` sans rien garder).
Sinon chaque « Entrée achat » est inversée par une « Annulation » (grand livre), l'achat est
barré (il garde son numéro, RG-T05) et le CMP / dernier coût des articles est rejoué sur le
stock réel (`refresh_costs`) — PUR-09 : P2 annulé, CMP revenu à 500 000. Journal « sensible ».
"""

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.purchasing.costs import refresh_costs
from app.application.purchasing.entries import live_entries, require_kept, reverse_entries
from app.application.purchasing.ports import PurchaseRepository
from app.application.purchasing.views import PurchaseView, view_of
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of
from app.application.stock.ledger import StockLedger
from app.application.stock.retry import with_stock_retry
from app.domain.purchasing.ids import PurchaseId


class CancelPurchase:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, policy: Policy, ledger: StockLedger, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._ledger = ledger
        self._clock = clock

    def execute(self, actor: Actor, purchase_id: PurchaseId, reason: str) -> PurchaseView:
        self._policy.require(actor, Permission.PURCHASE_CANCEL)  # avant toute lecture
        return with_stock_retry(lambda: self._attempt(actor, purchase_id, reason))

    def _attempt(self, actor: Actor, purchase_id: PurchaseId, reason: str) -> PurchaseView:
        now = self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            purchases = PurchaseRepository.within(uow)
            purchase = purchases.get(purchase_id)
            purchase.require_valid()
            entries = live_entries(uow, purchase.id)
            require_kept(uow, entries, {})
            purchase.cancel(reason, performer=performer_of(actor), now=now)
            purchases.update(purchase)
            reverse_entries(uow, self._ledger, purchase, entries, author_id=actor.user_id, now=now)
            refresh_costs(uow, (line.article_id for line in purchase.details.lines))
            uow.commit()
        return view_of(actor, purchase, self._clock.today())
