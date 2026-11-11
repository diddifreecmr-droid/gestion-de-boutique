"""`IdentityAuditRecorder` : les événements de l'identité au journal des boutiques (T10, TR-09).

Branché sur l'unité de travail **plateforme** (`IdentityUnitOfWork`), il reçoit chaque
événement de l'identité au `commit()`, avant la validation. Les entrées (règle d'inscription
de `identity_events.py`) sont écrites par une unité de boutique **jointe** : même transaction
que l'action (connexion, code provisoire, déconnexion à distance…). Une panne du journal annule
donc l'action elle-même ; aucun événement n'est perdu entre deux transactions.
"""

from app.application.audit.identity_events import identity_audit_entries
from app.application.audit.ports import AuditLog
from app.application.identity.ports import IdentityEventHandler, MembershipDirectory
from app.application.identity.uow import IdentityUnitOfWork
from app.application.ports.clock import Clock
from app.domain.identity.events import IdentityEvent


class IdentityAuditRecorder(IdentityEventHandler):
    def __init__(self, memberships: MembershipDirectory, clock: Clock) -> None:
        self._memberships = memberships
        self._clock = clock

    def handle(self, event: IdentityEvent, uow: IdentityUnitOfWork) -> None:
        for entry in identity_audit_entries(event, self._memberships, self._clock.now()):
            with uow.join_shop(entry.shop_id) as shop_uow:
                AuditLog.within(shop_uow).append(entry)
                shop_uow.commit()
