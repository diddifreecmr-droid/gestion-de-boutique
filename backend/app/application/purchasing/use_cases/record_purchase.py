"""UC-ACH-01 — Enregistrer un achat (comptable, propriétaire ; recette SCN-01 étape 1, SCN-02).

Dans **une** transaction : numéro `A-000001` (RG-T05), chiffrage (RG-T10, RG-X02), une « Entrée
achat » par ligne au lieu de réception par le grand livre (coût unitaire final), puis dernier
coût et CMP de chaque article réécrits par le rejeu (`refresh_costs`, RG-T11, RG-T12).

- Prix à plus de 30 % du dernier coût : `PRICE_GAP_CONFIRMATION_REQUIRED` (422) tant que
  `confirm_price_gap` n'est pas vrai (PUR-02).
- Idempotent (specs § 6.1) : un `purchase_id` déjà connu renvoie l'achat existant
  (`created=False`) sans second mouvement ni numéro consommé.
- Rejoué sur conflit de concurrence (stock, numéro, coûts de l'article : `with_stock_retry`).
"""

from dataclasses import dataclass
from datetime import datetime

from app.application.expenses.references import checked_capture_time
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.purchasing.costs import refresh_costs
from app.application.purchasing.entries import post_entries
from app.application.purchasing.ports import PurchaseRepository
from app.application.purchasing.price_gap import require_confirmed
from app.application.purchasing.resolver import PurchaseInput, PurchaseResolver
from app.application.purchasing.views import PurchaseView, view_of
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.security.roles import Role
from app.application.shops.context import actor_shop, performer_of
from app.application.stock.ledger import StockLedger
from app.application.stock.retry import with_stock_retry
from app.domain.purchasing.ids import PurchaseId
from app.domain.purchasing.purchase import Purchase
from app.domain.purchasing.values import Capture
from app.domain.shared.doc_number import DocType


@dataclass(frozen=True, slots=True, kw_only=True)
class RecordPurchaseCommand:
    data: PurchaseInput
    purchase_id: PurchaseId | None = None
    captured_at: datetime | None = None
    confirm_price_gap: bool = False


class RecordPurchase:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, policy: Policy, ledger: StockLedger, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._ledger = ledger
        self._clock = clock

    def execute(self, actor: Actor, command: RecordPurchaseCommand) -> tuple[PurchaseView, bool]:
        self._policy.require(actor, Permission.PURCHASE_WRITE)
        return with_stock_retry(lambda: self._attempt(actor, command))

    def _attempt(self, actor: Actor, command: RecordPurchaseCommand) -> tuple[PurchaseView, bool]:
        now, today = self._clock.now(), self._clock.today()
        with self._uow_factory(actor_shop(actor)) as uow:
            purchases = PurchaseRepository.within(uow)
            if command.purchase_id is not None:
                existing = purchases.find(command.purchase_id)
                if existing is not None:
                    return view_of(actor, existing, today), False
            resolver = PurchaseResolver(uow, today=today, is_owner=actor.role is Role.OWNER)
            details, costed = resolver.resolve(command.data)
            require_confirmed(
                enumerate(costed),
                lambda article_id: resolver.articles[article_id].last_cost,
                confirmed=command.confirm_price_gap,
            )
            capture = Capture(
                created_by=actor.user_id,
                device_id=actor.device_id,
                captured_at=checked_capture_time(command.captured_at, now),
                received_at=now,
            )
            purchase = Purchase.record(
                uow.shop_id,
                uow.numbering.next(DocType.PURCHASE),
                details,
                costed,
                capture,
                performer=performer_of(actor),
                purchase_id=command.purchase_id,
            )
            purchases.add(purchase)
            post_entries(uow, self._ledger, purchase, actor.user_id)
            refresh_costs(uow, (line.article_id for line in details.lines))
            uow.commit()
        return view_of(actor, purchase, today), True
