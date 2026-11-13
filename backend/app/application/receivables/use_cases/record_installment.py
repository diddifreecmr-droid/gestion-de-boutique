"""UC-CRE-03 — Enregistrer un versement (propriétaire ; vendeur sur ses créances ; SCN-07).

- Cible : la créance choisie (`receivable_id`), sinon **la plus ancienne** créance du client
  ayant un reste (En cours d'abord, puis En perte : récupération) — REC-03.
- Montant > 0 et ≤ reste (`OVERPAYMENT`, `details.remaining`) ; mode actif de la boutique ;
  référence facultative ; date aujourd'hui par défaut (RG-T09 : vendeur J-7, jamais future).
- Numéro `R-000001` continu par boutique (RG-T05), attribué dans la transaction : un refus
  ne consomme aucun numéro. Reste à 0 → Soldée ; créance En perte → « Récupération sur perte ».
- Idempotent par `installment_id` client (201 puis 200) ; rejoué sur course (`retry.py`).
- Module `receivables` éteint → 403 `MODULE_DISABLED` avant toute lecture (specs § 15.1).
"""

from dataclasses import dataclass
from datetime import date, datetime

from app.application.expenses.references import checked_capture_time
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWork, UnitOfWorkFactory
from app.application.receivables.access import (
    ReceivableView,
    require_in_scope,
    responsible_scope,
    view_of,
    visible_receivable,
)
from app.application.receivables.ports import ReceivableRepository
from app.application.receivables.retry import with_receivable_retry
from app.application.sales.ports import CustomerRepository
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.security.roles import Role
from app.application.shops.context import actor_shop, performer_of
from app.application.shops.modules import require_module
from app.application.shops.ports import PaymentModeRepository
from app.domain.profiles.modules import Module
from app.domain.purchasing.values import Capture
from app.domain.receivables.ids import InstallmentId, ReceivableId
from app.domain.receivables.installment import Installment
from app.domain.receivables.receivable import Receivable
from app.domain.receivables.values import ReceivableStatus
from app.domain.sales.ids import CustomerId
from app.domain.shared.business_day import validate_entry_date
from app.domain.shared.doc_number import DocType
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import UserId
from app.domain.shared.money import Money
from app.domain.shops.ids import PaymentModeId


@dataclass(frozen=True, slots=True, kw_only=True)
class InstallmentCommand:
    amount: int
    mode_id: PaymentModeId
    receivable_id: ReceivableId | None = None
    customer_id: CustomerId | None = None
    paid_on: date | None = None
    reference: str | None = None
    installment_id: InstallmentId | None = None
    captured_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class InstallmentResult:
    view: ReceivableView
    installment: Installment


def oldest_with_balance(receivables: list[Receivable]) -> Receivable:
    """Plus ancienne créance En cours, sinon En perte avec un reste (récupération)."""
    for status in (ReceivableStatus.OPEN, ReceivableStatus.WRITTEN_OFF):
        for receivable in receivables:  # déjà de la plus ancienne à la plus récente
            if receivable.status is status and receivable.remaining.amount > 0:
                return receivable
    msg = "Ce client n'a aucune créance avec un reste à payer"
    raise ValidationFailed(msg, details={"field": "customer_id"})


def active_mode(uow: UnitOfWork, mode_id: PaymentModeId) -> PaymentModeId:
    mode = PaymentModeRepository.within(uow).get(mode_id)
    if not mode.details.active:
        msg = "Mode de paiement désactivé : choisissez-en un autre"
        raise ValidationFailed(msg, details={"field": "mode_id"})
    return mode.id


class RecordInstallment:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, command: InstallmentCommand) -> tuple[InstallmentResult, bool]:
        responsible = responsible_scope(self._policy, actor, Permission.INSTALLMENT_CREATE)
        if (command.receivable_id is None) == (command.customer_id is None):
            msg = "Indiquez la créance ou le client du versement"
            raise ValidationFailed(msg, details={"field": "receivable_id"})
        return with_receivable_retry(lambda: self._attempt(actor, command, responsible))

    def _attempt(
        self, actor: Actor, command: InstallmentCommand, responsible: UserId | None
    ) -> tuple[InstallmentResult, bool]:
        now, today = self._clock.now(), self._clock.today()
        with self._uow_factory(actor_shop(actor)) as uow:
            require_module(uow, Module.RECEIVABLES)  # avant toute lecture (§ 15.1)
            receivables = ReceivableRepository.within(uow)
            if command.installment_id is not None:
                existing = receivables.find_by_installment(command.installment_id)
                if existing is not None:
                    require_in_scope(existing, responsible)
                    item = existing.installment(command.installment_id)
                    return InstallmentResult(view_of(uow, actor, existing, today), item), False
            receivable = self._target(uow, command, responsible)
            paid_on = validate_entry_date(
                command.paid_on or today, today, is_owner=actor.role is Role.OWNER
            )
            mode_id = active_mode(uow, command.mode_id)
            amount = Money.entry(command.amount, "amount")
            installment = Installment(
                id=command.installment_id or InstallmentId.new(),
                number=uow.numbering.next(DocType.RECEIPT),
                paid_on=paid_on,
                amount=amount,
                mode_id=mode_id,
                capture=Capture(
                    created_by=actor.user_id,
                    device_id=actor.device_id,
                    captured_at=checked_capture_time(command.captured_at, now),
                    received_at=now,
                ),
                nature=receivable.nature_for_next(),
                reference=command.reference,
            )
            receivable.record_installment(installment, performer=performer_of(actor))
            receivables.update(receivable)
            view = view_of(uow, actor, receivable, today)
            uow.commit()
        return InstallmentResult(view, installment), True

    @staticmethod
    def _target(
        uow: UnitOfWork, command: InstallmentCommand, responsible: UserId | None
    ) -> Receivable:
        if command.receivable_id is not None:
            return visible_receivable(uow, command.receivable_id, responsible)
        if command.customer_id is None:  # exclu par `execute` : défense en profondeur
            msg = "Client du versement manquant"
            raise ValidationFailed(msg, details={"field": "customer_id"})
        CustomerRepository.within(uow).get(command.customer_id)  # inconnu ici → 404 (SEC-I)
        found = ReceivableRepository.within(uow).for_customer(
            command.customer_id, responsible=responsible
        )
        return oldest_with_balance(found)
