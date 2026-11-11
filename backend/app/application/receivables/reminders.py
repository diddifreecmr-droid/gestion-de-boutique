"""UC-CRE-06 / TR-19 — Alerter les rappels du jour (tâche planifiée idempotente, REM-01).

`DispatchDueReminders.execute(shop_id, today)` est appelé par le worker (une fois par
boutique, chaque jour, à toute heure) : chaque rappel non fait dont la date est passée ou
arrivée, sur une créance non annulée, dépose `ReminderDue` (alerte « Rappel créance » au
vendeur responsable et aux propriétaires actifs, règle `reminder_due`) puis retient la date
alertée (`alerted_for`). **Idempotence** : relancer la tâche ne réalerte jamais la même date
(`alerted_for`), et la clé `receivable_reminder:<rappel>:<date>` déduplique en plus une course
entre deux workers. Un rappel reporté réalerte à sa nouvelle date. Aucun message n'est envoyé
au client (H19 : aucun port d'envoi n'existe).
"""

from collections.abc import Iterable
from datetime import date

from app.application.alerts.dispatcher import AlertDirective, AlertDispatcher, AlertNotice
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWork, UnitOfWorkFactory
from app.application.receivables.ports import ReceivableRepository
from app.application.receivables.retry import with_receivable_retry
from app.application.sales.ports import CustomerRepository
from app.application.stock.alerts import OWNERS, recipients
from app.domain.alerts.alert import AlertType
from app.domain.receivables.events import ReminderDue
from app.domain.receivables.values import ReceivableStatus
from app.domain.shared.ids import ShopId


def reminder_key(event: ReminderDue) -> str:
    return f"receivable_reminder:{event.reminder_id}:{event.remind_on.isoformat()}"


def reminder_due(event: ReminderDue, uow: UnitOfWork) -> Iterable[AlertDirective]:
    targets = recipients(uow, OWNERS)
    if event.responsible_seller_id is not None:
        targets = [event.responsible_seller_id, *targets]
    return [
        AlertNotice(
            recipients=targets,
            type=AlertType.RECEIVABLE_REMINDER,
            entity=event.entity,
            message=event.message,
            dedup_key=reminder_key(event),
        )
    ]


def register_receivable_alerts(dispatcher: AlertDispatcher) -> None:
    """À appeler **une fois** par répartiteur (composition root, `bootstrap/core.py`)."""
    dispatcher.register(ReminderDue, reminder_due)


class DispatchDueReminders:
    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    def execute(self, shop_id: ShopId, today: date) -> int:
        """Nombre de rappels alertés par cet appel (0 au second passage du même jour)."""
        return with_receivable_retry(lambda: self._attempt(shop_id, today))

    def _attempt(self, shop_id: ShopId, today: date) -> int:
        now, count = self._clock.now(), 0
        with self._uow_factory(shop_id) as uow:
            receivables = ReceivableRepository.within(uow)
            customers = CustomerRepository.within(uow)
            for receivable in receivables.with_due_reminders(today):
                if receivable.status is ReceivableStatus.CANCELLED:
                    continue  # le dépôt les exclut déjà : défense en profondeur
                due = [r for r in receivable.reminders if r.is_due(today)]
                if not due:
                    continue
                customer = customers.get(receivable.customer_id).name
                for reminder in due:
                    note = f" — {reminder.note}" if reminder.note else ""
                    message = f"Rappel créance : {customer}, reste {receivable.remaining}{note}"
                    receivable.mark_reminder_alerted(reminder.id, now=now, message=message)
                    count += 1
                receivables.update(receivable)
            uow.commit()
        return count
