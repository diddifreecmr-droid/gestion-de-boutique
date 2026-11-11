"""Port `AlertRepository` : alertes de la boutique, par destinataire (UC-SOC-09, ALR-01 à 04).

Unicité `ALERT_ACTIVE_DEDUP` : un destinataire n'a jamais deux alertes **actives** de même
`dedup_key` (clé `(recipient_id, dedup_active_key)`, non contrainte si la clé est vide). Les
lectures suivent les agrégats renvoyés (`update` possible ensuite, ex. `mark_read`).
"""

from abc import abstractmethod
from collections.abc import Sequence

from app.application.ports.aggregate import UniqueKey
from app.application.ports.pagination import Cursor, Page, PageRequest
from app.application.ports.repository import Repository
from app.domain.alerts.alert import Alert, AlertId
from app.domain.shared.ids import UserId

ALERT_ACTIVE_DEDUP = "alert_active_dedup"
"""Nom de la contrainte d'unicité, identique dans l'adaptateur SQL (`tables.alert`)."""


def active_dedup(alert: Alert) -> tuple[UserId, str] | None:
    key = alert.dedup_active_key
    return None if key is None else (alert.recipient_id, key)


def alert_position(alert: Alert) -> Cursor:
    """Position d'une alerte dans la liste (plus récente d'abord)."""
    return Cursor(alert.created_at, alert.id.value)


class AlertRepository(Repository[AlertId, Alert]):
    def unique_keys(self) -> Sequence[UniqueKey[Alert]]:
        return (UniqueKey(ALERT_ACTIVE_DEDUP, active_dedup),)

    @abstractmethod
    def for_recipient(
        self, recipient_id: UserId, page: PageRequest, *, unread_only: bool = False
    ) -> Page[Alert]:
        """Alertes du destinataire, plus récentes d'abord."""

    @abstractmethod
    def unread_count(self, recipient_id: UserId) -> int:
        """Nombre d'alertes non lues du destinataire (pastille de la cloche, ALR-01)."""

    @abstractmethod
    def find_active(self, recipient_id: UserId, dedup_key: str) -> Alert | None:
        """Alerte active de ce destinataire portant `dedup_key`, s'il y en a une."""

    @abstractmethod
    def active_with_key(self, dedup_key: str) -> list[Alert]:
        """Toutes les alertes actives portant `dedup_key` (tous destinataires)."""

    def _tracked(self, alerts: Sequence[Alert]) -> list[Alert]:
        """À appeler par les requêtes des adaptateurs sur chaque agrégat renvoyé."""
        for alert in alerts:
            self._tracker.track(alert, saved=False)
        return list(alerts)
