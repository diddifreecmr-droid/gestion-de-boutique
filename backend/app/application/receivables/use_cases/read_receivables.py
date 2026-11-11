"""UC-CRE-04 — Consulter les créances ; lire une créance (REC-04, REC-05 ; M18).

- En tête (sur la portée de l'acteur, filtres non appliqués) : **total à recevoir** (restes
  des créances En cours), **nombre de clients débiteurs** (clients ayant une créance En
  cours), **versements reçus aujourd'hui** (versements valides datés du jour).
- Liste : tri par **reste décroissant** (puis ouverture la plus ancienne). Filtres : statut,
  vendeur responsable, tranche d'ancienneté (Q-19), rappel dépassé (rappel non fait daté
  d'avant aujourd'hui), sans versement depuis plus de 30 jours (dernier versement, ou
  ouverture à défaut, avant J-30). Liste complète, sans pagination (quelques centaines de
  créances par boutique au Lot 1).
- Le vendeur ne voit que ses créances (portée « Siennes » dans la requête) ; la créance d'un
  autre → 404.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.receivables.access import (
    ReceivableView,
    responsible_scope,
    view_of,
    visible_receivable,
)
from app.application.receivables.ports import ReceivableRepository
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.domain.receivables.follow_up import ReminderStatus
from app.domain.receivables.ids import ReceivableId
from app.domain.receivables.receivable import Receivable
from app.domain.receivables.values import ReceivableStatus, SeniorityBand, seniority_band
from app.domain.shared.ids import UserId
from app.domain.shared.money import Money

QUIET_DAYS = 30


@dataclass(frozen=True, slots=True, kw_only=True)
class ReceivableCriteria:
    status: ReceivableStatus | None = None
    seller_id: UserId | None = None
    band: SeniorityBand | None = None
    reminder_overdue: bool = False
    quiet: bool = False
    """Sans versement depuis plus de 30 jours."""

    def matches(self, receivable: Receivable, today: date) -> bool:
        if self.status is not None and receivable.status is not self.status:
            return False
        if self.seller_id is not None and receivable.responsible_seller_id != self.seller_id:
            return False
        if self.band is not None and seniority_band(receivable.seniority(today)) != self.band:
            return False
        if self.reminder_overdue and not overdue(receivable, today):
            return False
        last = receivable.last_installment_on or receivable.opened_on
        return not self.quiet or last < today - timedelta(days=QUIET_DAYS)


def overdue(receivable: Receivable, today: date) -> bool:
    return any(
        r.status is not ReminderStatus.DONE and r.remind_on < today for r in receivable.reminders
    )


@dataclass(frozen=True, slots=True)
class ReceivableSummary:
    total_due: Money
    debtor_count: int
    received_today: Money


@dataclass(frozen=True, slots=True)
class ReceivableListing:
    summary: ReceivableSummary
    items: list[ReceivableView]


def summary_of(receivables: list[Receivable], today: date) -> ReceivableSummary:
    due = [r for r in receivables if r.counts_as_due]
    received = Money.total(
        i.amount for r in receivables for i in r.installments if i.valid and i.paid_on == today
    )
    return ReceivableSummary(
        total_due=Money.total(r.remaining for r in due),
        debtor_count=len({r.customer_id for r in due}),
        received_today=received,
    )


class ListReceivables:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, criteria: ReceivableCriteria) -> ReceivableListing:
        responsible = responsible_scope(self._policy, actor, Permission.RECEIVABLE_READ)
        today = self._clock.today()
        with self._uow_factory(actor_shop(actor)) as uow:
            found = ReceivableRepository.within(uow).list_all(responsible=responsible)
            kept = [r for r in found if criteria.matches(r, today)]
            kept.sort(key=lambda r: (-r.remaining.amount, r.opened_on, r.id.value))
            items = [view_of(uow, actor, r, today) for r in kept]
        return ReceivableListing(summary_of(found, today), items)


class GetReceivable:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, receivable_id: ReceivableId) -> ReceivableView:
        responsible = responsible_scope(self._policy, actor, Permission.RECEIVABLE_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            receivable = visible_receivable(uow, receivable_id, responsible)
            return view_of(uow, actor, receivable, self._clock.today())
