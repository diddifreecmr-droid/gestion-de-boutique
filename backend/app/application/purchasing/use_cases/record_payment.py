"""UC-ACH-06 — Noter le paiement d'un achat (comptable, propriétaire ; recette PUR-12).

Date (aujourd'hui par défaut, RG-T09), montant > 0, mode de paiement **actif** de la boutique,
référence facultative. Le total payé ne dépasse jamais le total (`OVERPAYMENT`, 422 :
10 800 000 → 4 000 000 « Payé en partie », + 6 800 000 « Payé », + 1 refusé). Achat annulé :
`INVALID_STATE_TRANSITION`. Idempotent par `payment_id` client (rejeu : `created=False`).
"""

from dataclasses import dataclass
from datetime import date

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.purchasing.ports import PurchaseRepository
from app.application.purchasing.resolver import inactive
from app.application.purchasing.views import PurchaseView, view_of
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.security.roles import Role
from app.application.shops.context import actor_shop, performer_of
from app.application.shops.ports import PaymentModeRepository
from app.domain.purchasing.ids import PurchaseId, SupplierPaymentId
from app.domain.purchasing.payment_rules import add_payment
from app.domain.purchasing.payments import SupplierPayment
from app.domain.shared.business_day import validate_entry_date
from app.domain.shared.money import Money
from app.domain.shops.ids import PaymentModeId


@dataclass(frozen=True, slots=True, kw_only=True)
class PaymentCommand:
    purchase_id: PurchaseId
    amount: int
    mode_id: PaymentModeId
    paid_on: date | None = None
    reference: str | None = None
    payment_id: SupplierPaymentId | None = None


class RecordSupplierPayment:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, command: PaymentCommand) -> tuple[PurchaseView, bool]:
        self._policy.require(actor, Permission.PURCHASE_WRITE)
        now, today = self._clock.now(), self._clock.today()
        with self._uow_factory(actor_shop(actor)) as uow:
            purchases = PurchaseRepository.within(uow)
            purchase = purchases.get(command.purchase_id)
            payment_id = command.payment_id or SupplierPaymentId.new()
            if any(payment.id == payment_id for payment in purchase.payments):
                return view_of(actor, purchase, today), False
            mode = PaymentModeRepository.within(uow).get(command.mode_id)
            if not mode.details.active:
                raise inactive("mode_id")
            paid_on = command.paid_on or today
            validate_entry_date(paid_on, today, is_owner=actor.role is Role.OWNER)
            payment = SupplierPayment(
                id=payment_id,
                paid_on=paid_on,
                amount=Money.entry(command.amount, "amount"),
                mode_id=mode.id,
                recorded_at=now,
                recorded_by=actor.user_id,
                reference=command.reference,
            )
            add_payment(purchase, payment, performer=performer_of(actor))
            purchases.update(purchase)
            uow.commit()
        return view_of(actor, purchase, today), True
