"""`AuditRecorder` : handler qui inscrit au journal chaque événement, **dans la transaction**.

Branché sur l'unité de travail (`handlers=[AuditRecorder(clock), …]`), il reçoit chaque
événement au `commit()`, avant la validation (D7, TR-09) :

- `AuditableEvent` → une entrée, `received_at` = horloge du serveur, `captured_at` = celui que
  déclare l'événement (heure de l'appareil) ou, à défaut, `occurred_at` ;
- `NotAudited` → rien, par décision explicite de l'événement ;
- tout autre événement → `UnauditedEvent` : la transaction entière est annulée (fail-fast).

Une panne du journal (écriture refusée, traduction en erreur) annule l'action elle-même : le
gabarit `UnitOfWork` le garantit, `tests/contracts/test_audit_recorder_contract.py` le prouve.
"""

from app.application.audit.ports import AuditLog
from app.application.ports.clock import Clock
from app.application.ports.event_handler import EventHandler
from app.application.ports.uow import UnitOfWork
from app.domain.audit.entry import AuditEntry
from app.domain.audit.events import AuditableEvent, NotAudited, UnauditedEvent
from app.domain.shared.events import DomainEvent


class AuditRecorder(EventHandler):
    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def handle(self, event: DomainEvent, uow: UnitOfWork) -> None:
        if isinstance(event, NotAudited):
            return
        if not isinstance(event, AuditableEvent):
            msg = (
                f"{type(event).__name__} : ni AuditableEvent ni NotAudited — décider de sa "
                "journalisation (RG-T01)"
            )
            raise UnauditedEvent(msg)
        entry = AuditEntry.inscribe(
            event.shop_id,
            event.audit_record(),
            received_at=self._clock.now(),
            default_captured_at=event.occurred_at,
        )
        AuditLog.within(uow).append(entry)
