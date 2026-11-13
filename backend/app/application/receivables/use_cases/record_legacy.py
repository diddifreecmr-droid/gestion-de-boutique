"""UC-CRE-02 — Enregistrer une créance ancienne (propriétaire seul, Q-15 ; SCN-08 étape 1).

Client existant (`customer.customer_id`) ou création rapide nom + téléphone (même règle que
la vente : un téléphone connu réutilise la fiche). Montant dû aujourd'hui (> 0), date
d'origine (passé illimité, jamais future : RG-T09), description obligatoire, vendeur
responsable facultatif (membre actif vendeur ou propriétaire), conditions. Aucune vente,
aucun mouvement de stock : elle ne compte ni dans les ventes ni dans les marges.
Idempotent par `receivable_id` client (201 puis 200).

`open_legacy` : le même enregistrement **dans l'unité de travail de l'appelant**, sans `add`
ni `commit` — repris tel quel par l'import « Créances en cours » (T34), qui écrit tout un lot
dans une seule transaction.
"""

from dataclasses import dataclass
from datetime import date, datetime

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWork, UnitOfWorkFactory
from app.application.receivables.access import ReceivableView, view_of
from app.application.receivables.ports import ReceivableRepository
from app.application.sales.inputs import CustomerInput
from app.application.sales.resolver import SELLING_ROLES, sale_customer
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of
from app.application.shops.ports import MembershipRepository
from app.domain.receivables.ids import ReceivableId
from app.domain.receivables.receivable import Receivable
from app.domain.receivables.values import ReceivableOrigin
from app.domain.shared.business_day import validate_entry_date
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import UserId
from app.domain.shared.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class LegacyReceivableCommand:
    customer: CustomerInput
    amount: int
    opened_on: date
    description: str
    responsible_seller_id: UserId | None = None
    terms: str | None = None
    receivable_id: ReceivableId | None = None


def require_seller(uow: UnitOfWork, user_id: UserId | None) -> UserId | None:
    """Vendeur responsable : membre actif vendeur ou propriétaire de la boutique."""
    if user_id is None:
        return None
    membership = MembershipRepository.within(uow).find_by_user(user_id)
    if membership is None or not membership.active or membership.role not in SELLING_ROLES:
        msg = "Vendeur responsable inconnu ou inactif dans cette boutique"
        raise ValidationFailed(msg, details={"field": "responsible_seller_id"})
    return user_id


def open_legacy(
    uow: UnitOfWork,
    actor: Actor,
    command: LegacyReceivableCommand,
    *,
    now: datetime,
    today: date,
) -> Receivable:
    """Créance ancienne prête à être ajoutée (client créé si son téléphone est inconnu)."""
    customer = sale_customer(uow, actor, command.customer, now)
    if customer is None:  # exclu par le type de `customer` : défense en profondeur
        msg = "Client obligatoire"
        raise ValidationFailed(msg, details={"field": "customer"})
    return Receivable.open_legacy(
        uow.shop_id,
        receivable_id=command.receivable_id or ReceivableId.new(),
        customer_id=customer.id,
        amount=Money.entry(command.amount, "amount"),
        opened_on=validate_entry_date(command.opened_on, today, is_owner=True),
        description=command.description,
        responsible_seller_id=require_seller(uow, command.responsible_seller_id),
        terms=command.terms,
        performer=performer_of(actor),
        now=now,
    )


class RecordLegacyReceivable:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(
        self, actor: Actor, command: LegacyReceivableCommand
    ) -> tuple[ReceivableView, bool]:
        self._policy.require(actor, Permission.RECEIVABLE_CREATE)
        now, today = self._clock.now(), self._clock.today()
        with self._uow_factory(actor_shop(actor)) as uow:
            receivables = ReceivableRepository.within(uow)
            if command.receivable_id is not None:
                existing = receivables.find(command.receivable_id)
                if existing is not None and existing.origin is ReceivableOrigin.LEGACY:
                    return view_of(uow, actor, existing, today), False
            receivable = open_legacy(uow, actor, command, now=now, today=today)
            receivables.add(receivable)
            view = view_of(uow, actor, receivable, today)
            uow.commit()
        return view, True
