"""UC-SOC-09 — lister ses alertes, compter les non lues, en marquer une lue (ALR-01, ALR-03).

Droit `ALERT_READ` : « Tous », chacun **les siennes** — le filtre par destinataire vaut aussi
pour le propriétaire (la cloche compte les alertes de l'utilisateur dans la boutique active).
L'alerte d'un autre destinataire est introuvable (404), comme un identifiant inexistant.
"""

from dataclasses import dataclass

from app.application.alerts.ports import AlertRepository
from app.application.ports.pagination import Page, PageRequest
from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.domain.alerts.alert import Alert, AlertId
from app.domain.shared.ids import ShopId


@dataclass(frozen=True, slots=True)
class AlertList:
    page: Page[Alert]
    unread_count: int


def _shop(actor: Actor) -> ShopId:
    if actor.shop_id is None:  # exclu par la Policy (admin hors boutique) : défense
        msg = "Alertes sans boutique active"
        raise RuntimeError(msg)
    return actor.shop_id


class ListAlerts:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy) -> None:
        self._uow_factory = uow_factory
        self._policy = policy

    def execute(self, actor: Actor, page: PageRequest, *, unread_only: bool = False) -> AlertList:
        self._policy.require(actor, Permission.ALERT_READ)
        with self._uow_factory(_shop(actor)) as uow:
            alerts = AlertRepository.within(uow)
            return AlertList(
                page=alerts.for_recipient(actor.user_id, page, unread_only=unread_only),
                unread_count=alerts.unread_count(actor.user_id),
            )


class MarkAlertRead:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy) -> None:
        self._uow_factory = uow_factory
        self._policy = policy

    def execute(self, actor: Actor, alert_id: AlertId) -> int:
        """Marque l'alerte lue (idempotent) ; renvoie le nouveau nombre de non lues."""
        self._policy.require(actor, Permission.ALERT_READ)
        with self._uow_factory(_shop(actor)) as uow:
            alerts = AlertRepository.within(uow)
            alert = alerts.get(alert_id)
            if alert.recipient_id != actor.user_id:
                raise not_found(alert_id)  # alerte d'un autre : même 404 qu'inexistante
            if alert.mark_read():
                alerts.update(alert)
            remaining = alerts.unread_count(actor.user_id)
            uow.commit()
        return remaining
