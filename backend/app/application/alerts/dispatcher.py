"""`AlertDispatcher` : handler générique qui crée ou résout des alertes dans la transaction.

Il ne contient **aucune règle métier** : chaque module branche les siennes (T14 stock bas,
T16 erreur signalée…) par `register(TypeDEvénement, règle)`. Une règle reçoit l'événement et
l'unité de travail (pour lire, ex. les destinataires) et renvoie des directives :

- `AlertNotice` : une alerte par destinataire. Avec `dedup_key`, un destinataire qui a déjà
  une alerte **active** de même clé n'en reçoit pas d'autre (UC-STK-09 « une seule fois ») ;
- `AlertResolution` : la condition a cessé, les alertes actives de cette clé sont résolues
  (la clé redevient libre : la prochaine baisse de stock alertera de nouveau).

Concurrence : deux transactions qui créent la même alerte active → la seconde écriture viole
`ALERT_ACTIVE_DEDUP`. Sur PostgreSQL l'écriture attend la première puis échoue dans son
savepoint : la règle « une seule fois » est alors déjà satisfaite, l'alerte n'est pas recréée
et la transaction métier continue. Toute autre violation remonte. L'adaptateur mémoire ne
détecte cette course qu'au commit (`Duplicate`, transaction à rejouer).
"""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from app.application.alerts.ports import ALERT_ACTIVE_DEDUP, AlertRepository
from app.application.ports.clock import Clock
from app.application.ports.event_handler import EventHandler
from app.application.ports.uow import UnitOfWork
from app.domain.alerts.alert import Alert, AlertType
from app.domain.audit.values import EntityRef
from app.domain.shared.errors import Duplicate
from app.domain.shared.events import DomainEvent
from app.domain.shared.ids import UserId


@dataclass(frozen=True, slots=True, kw_only=True)
class AlertNotice:
    recipients: Sequence[UserId]
    type: AlertType
    entity: EntityRef
    message: str
    dedup_key: str | None = None


@dataclass(frozen=True, slots=True)
class AlertResolution:
    dedup_key: str


type AlertDirective = AlertNotice | AlertResolution
type AlertRule[E: DomainEvent] = Callable[[E, UnitOfWork], Iterable[AlertDirective]]


class AlertDispatcher(EventHandler):
    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._rules: list[tuple[type[DomainEvent], Callable[[Any, UnitOfWork], Any]]] = []

    def register[E: DomainEvent](self, event_type: type[E], rule: AlertRule[E]) -> None:
        """Ajoute une règle pour `event_type` (et ses sous-classes), dans l'ordre d'appel."""
        if not (isinstance(event_type, type) and issubclass(event_type, DomainEvent)):
            msg = f"register attend un type de DomainEvent, reçu {event_type!r}"
            raise TypeError(msg)
        self._rules.append((event_type, rule))

    def handle(self, event: DomainEvent, uow: UnitOfWork) -> None:
        for event_type, rule in self._rules:
            if not isinstance(event, event_type):
                continue
            for directive in rule(event, uow):
                self._apply(directive, uow)

    def _apply(self, directive: AlertDirective, uow: UnitOfWork) -> None:
        if not isinstance(directive, AlertNotice | AlertResolution):
            msg = f"Directive d'alerte inconnue : {type(directive).__name__}"
            raise TypeError(msg)
        alerts = AlertRepository.within(uow)
        if isinstance(directive, AlertResolution):
            for alert in alerts.active_with_key(directive.dedup_key):
                alert.resolve(self._clock.now())
                alerts.update(alert)
            return
        for recipient in dict.fromkeys(directive.recipients):  # sans doublon, ordre conservé
            self._notify(alerts, recipient, directive, uow)

    def _notify(
        self, alerts: AlertRepository, recipient: UserId, notice: AlertNotice, uow: UnitOfWork
    ) -> None:
        key = notice.dedup_key
        if key is not None and alerts.find_active(recipient, key) is not None:
            return  # déjà alerté, condition toujours vraie : « une seule fois »
        alert = Alert.raise_for(
            shop_id=uow.shop_id,
            recipient_id=recipient,
            type=notice.type,
            entity=notice.entity,
            message=notice.message,
            now=self._clock.now(),
            dedup_key=key,
        )
        try:
            alerts.add(alert)
        except Duplicate as exc:
            if exc.details.get("constraint") == ALERT_ACTIVE_DEDUP:
                return  # créée entre-temps par une transaction concurrente : déjà alerté
            raise
