"""UC-CRE-08 — Annuler un versement ; UC-CRE-09 — Passer une créance en perte (propriétaire).

- Annulation (`INSTALLMENT_CANCEL`) : motif obligatoire (400) ; le versement reste visible,
  barré ; le reste est recalculé et une créance Soldée redevient En cours (SCN-07 étape 7).
  Dans les chiffres, l'annulation compte **le jour où elle est faite** (Q-09).
- Mise en perte (`RECEIVABLE_WRITE_OFF`) : motif obligatoire, créance En cours seulement
  (`INVALID_STATE_TRANSITION` sinon, SCN-08 étape 7) ; date = aujourd'hui (Douala) ; elle sort
  du total à recevoir ; journal sensible.
"""

from dataclasses import dataclass

from app.application.ports.clock import Clock
from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWorkFactory
from app.application.receivables.access import ReceivableView, view_of
from app.application.receivables.ports import ReceivableRepository
from app.application.receivables.retry import with_receivable_retry
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of
from app.domain.receivables.ids import InstallmentId, ReceivableId
from app.domain.receivables.installment import Installment


@dataclass(frozen=True, slots=True)
class CancelledInstallment:
    view: ReceivableView
    installment: Installment


class CancelInstallment:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(
        self, actor: Actor, installment_id: InstallmentId, reason: str
    ) -> CancelledInstallment:
        self._policy.require(actor, Permission.INSTALLMENT_CANCEL)
        return with_receivable_retry(lambda: self._attempt(actor, installment_id, reason))

    def _attempt(
        self, actor: Actor, installment_id: InstallmentId, reason: str
    ) -> CancelledInstallment:
        now = self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            receivables = ReceivableRepository.within(uow)
            receivable = receivables.find_by_installment(installment_id)
            if receivable is None:
                raise not_found(installment_id)
            cancelled = receivable.cancel_installment(
                installment_id, reason, performer=performer_of(actor), now=now
            )
            receivables.update(receivable)
            view = view_of(uow, actor, receivable, self._clock.today())
            uow.commit()
        return CancelledInstallment(view, cancelled)


class WriteOffReceivable:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, receivable_id: ReceivableId, reason: str) -> ReceivableView:
        self._policy.require(actor, Permission.RECEIVABLE_WRITE_OFF)
        return with_receivable_retry(lambda: self._attempt(actor, receivable_id, reason))

    def _attempt(self, actor: Actor, receivable_id: ReceivableId, reason: str) -> ReceivableView:
        now, today = self._clock.now(), self._clock.today()
        with self._uow_factory(actor_shop(actor)) as uow:
            receivables = ReceivableRepository.within(uow)
            receivable = receivables.get(receivable_id)
            receivable.mark_written_off(reason, on=today, performer=performer_of(actor), now=now)
            receivables.update(receivable)
            view = view_of(uow, actor, receivable, today)
            uow.commit()
        return view
