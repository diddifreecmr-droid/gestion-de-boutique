"""`AlertRepository` mémoire (gabarit `MemoryRepository` + requêtes par destinataire)."""

import copy
from typing import cast

from app.application.alerts.ports import AlertRepository, alert_position
from app.application.ports.pagination import Page, PageRequest, paginate
from app.domain.alerts.alert import Alert, AlertId
from app.domain.shared.ids import UserId
from app.infrastructure.persistence.memory.repository import MemoryRepository


class MemoryAlertRepository(MemoryRepository[AlertId, Alert], AlertRepository):
    table = "alerts"

    def _all(self) -> list[Alert]:
        # Les lignes de cette table ne sont construites que par `_row` à partir d'une Alert.
        rows = self._transaction.rows(self.table)
        return [cast(Alert, copy.deepcopy(row.payload)) for row in rows]

    def for_recipient(
        self, recipient_id: UserId, page: PageRequest, *, unread_only: bool = False
    ) -> Page[Alert]:
        mine = [
            alert
            for alert in self._all()
            if alert.recipient_id == recipient_id and not (unread_only and alert.read)
        ]
        ordered = sorted(mine, key=alert_position, reverse=True)
        found = paginate(ordered, page, alert_position)
        return Page(self._tracked(found.items), found.next_cursor)

    def unread_count(self, recipient_id: UserId) -> int:
        return sum(1 for a in self._all() if a.recipient_id == recipient_id and not a.read)

    def find_active(self, recipient_id: UserId, dedup_key: str) -> Alert | None:
        matches = [
            alert
            for alert in self._all()
            if alert.recipient_id == recipient_id and alert.dedup_active_key == dedup_key
        ]
        return self._tracked(matches)[0] if matches else None

    def active_with_key(self, dedup_key: str) -> list[Alert]:
        matches = [alert for alert in self._all() if alert.dedup_active_key == dedup_key]
        return self._tracked(sorted(matches, key=alert_position))
