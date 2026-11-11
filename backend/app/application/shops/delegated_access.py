"""Journal des accès de l'administrateur sous délégation (specs § 8.3, recette SEC-I11).

`Authenticate.actor_for` appelle `record(actor)` à **chaque** requête de l'administrateur sur une
boutique dont la délégation court : une entrée « Se connecter » sensible est écrite dans le
journal de cette boutique, dans sa propre transaction (la requête n'a pas encore commencé).
Le propriétaire voit ainsi chaque consultation. Un échec d'écriture fait échouer la requête.
"""

from app.application.audit.ports import AuditLog
from app.application.identity.ports import DelegatedAccessJournal
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.shops.context import actor_shop, performer_of
from app.domain.audit.entry import AuditEntry, AuditRecord
from app.domain.audit.values import AuditAction, EntityRef

MODULE = "security"
SUMMARY = "Consultation par l'administrateur plateforme (délégation du propriétaire)"


class AuditDelegatedAccess(DelegatedAccessJournal):
    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    def record(self, actor: Actor) -> None:
        if not actor.is_platform_admin or actor.delegation is None:
            msg = "Seul un accès de l'administrateur sous délégation est journalisé ici"
            raise ValueError(msg)
        shop_id, now = actor_shop(actor), self._clock.now()
        record = AuditRecord(
            performer=performer_of(actor),
            action=AuditAction.LOGIN,
            entity=EntityRef("shop", shop_id.value),
            module=MODULE,
            summary=SUMMARY,
            sensitive=True,
            captured_at=now,
        )
        entry = AuditEntry.inscribe(shop_id, record, received_at=now, default_captured_at=now)
        with self._uow_factory(shop_id) as uow:
            AuditLog.within(uow).append(entry)
            uow.commit()
