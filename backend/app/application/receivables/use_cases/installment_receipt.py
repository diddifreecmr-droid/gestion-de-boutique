"""UC-CRE-03 étape 4 — Reçu de versement (DTO à imprimer ou partager ; SCN-07).

Contenu : boutique (nom, ville, téléphone), numéro `R-…`, date, client (nom, téléphone),
montant, mode, référence, **total déjà versé** (acompte de la vente + versements valides
jusqu'à celui-ci inclus : SCN-07 → 500 000 après un versement de 200 000 sur un acompte de
300 000), **reste à payer** après ce versement, mention « Soldé » quand ce reste est nul,
nature (« Récupération sur perte »), versement annulé (barré). Aucun coût n'y figure.
Même portée que la lecture des créances (vendeur : ses créances, sinon 404).
"""

from dataclasses import dataclass
from datetime import date

from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWorkFactory
from app.application.receivables.access import require_in_scope, responsible_scope
from app.application.receivables.ports import ReceivableRepository
from app.application.sales.ports import CustomerRepository
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.application.shops.ports import PaymentModeRepository, ShopRepository
from app.domain.receivables.ids import InstallmentId
from app.domain.receivables.installment import Installment
from app.domain.shared.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class InstallmentReceipt:
    shop_name: str
    shop_city: str | None
    shop_phone: str | None
    installment: Installment
    paid_on: date
    customer_name: str
    customer_phone: str
    mode_name: str
    total_paid: Money
    remaining: Money
    sale_number: str | None

    @property
    def settled(self) -> bool:
        return self.remaining.amount == 0 and self.installment.valid


class GetInstallmentReceipt:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy) -> None:
        self._uow_factory = uow_factory
        self._policy = policy

    def execute(self, actor: Actor, installment_id: InstallmentId) -> InstallmentReceipt:
        responsible = responsible_scope(self._policy, actor, Permission.RECEIVABLE_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            receivable = ReceivableRepository.within(uow).find_by_installment(installment_id)
            if receivable is None:
                raise not_found(installment_id)
            require_in_scope(receivable, responsible)
            customer = CustomerRepository.within(uow).get(receivable.customer_id)
            shop = ShopRepository.within(uow).current()
            item = receivable.installment(installment_id)
            mode = PaymentModeRepository.within(uow).get(item.mode_id)
        rank = (item.paid_on, str(item.number))
        before = Money.total(
            i.amount
            for i in receivable.installments
            if i.valid and (i.paid_on, str(i.number)) <= rank and i.id != item.id
        )
        paid = before + (item.amount if item.valid else Money.zero())
        return InstallmentReceipt(
            shop_name=shop.name,
            shop_city=shop.identity.city,
            shop_phone=shop.identity.phone.e164,
            installment=item,
            paid_on=item.paid_on,
            customer_name=customer.name,
            customer_phone=customer.phone_key,
            mode_name=mode.name,
            total_paid=receivable.paid_at_sale + paid,
            remaining=receivable.initial_amount - paid,
            sale_number=receivable.sale_number,
        )
