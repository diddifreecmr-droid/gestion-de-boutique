"""Journalisation des refus d'accès (RG-D01, TR-04, specs § 6.2 « inscrit au journal »).

L'interface HTTP appelle `RecordAccessDenied.execute(error)` quand un cas d'utilisation lève
`PermissionDenied`, `ShopAccessDenied` ou `PlatformAdminRequired`. Le refus survient en général
avant toute transaction (ou l'a annulée) : l'entrée est écrite dans **sa propre** transaction.

Où s'inscrit le refus (décision Q-23) :

- l'acteur est **membre** de la boutique visée (rôle relu) → journal de cette boutique ;
- l'acteur est l'administrateur avec une **délégation active** pour cette boutique → journal
  de cette boutique (specs § 8.3 : chaque accès de l'admin est journalisé) ;
- sinon (admin sans délégation, console plateforme) → **journal plateforme minimal** : une
  ligne structurée sur le journal serveur `app.audit.platform` (niveau WARNING). On n'écrit
  rien dans une boutique où l'acteur n'a aucun lien : son propriétaire n'a pas à voir les
  tentatives d'un tiers, et l'existence de la boutique ne fuit pas.

Un non-membre est arrêté plus tôt, par `Authenticate.actor_for` (404 sans `Actor`) : aucune
boutique ne reçoit d'entrée ; ce cas relève de la limitation de débit, pas du journal.
"""

import logging
from datetime import datetime

from app.application.audit.ports import AuditLog
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.errors import (
    PermissionDenied,
    PlatformAdminRequired,
    ShopAccessDenied,
    role_label,
)
from app.domain.audit.entry import AuditEntry, AuditRecord
from app.domain.audit.values import AuditAction, EntityRef, Performer
from app.domain.shared.ids import ShopId

platform_log = logging.getLogger("app.audit.platform")

type AccessDenial = PermissionDenied | ShopAccessDenied | PlatformAdminRequired
ACCESS_DENIALS = (PermissionDenied, ShopAccessDenied, PlatformAdminRequired)

MODULE = "security"
ENTITY_TYPE = "permission"


def _permission_code(error: AccessDenial) -> str:
    if isinstance(error, PlatformAdminRequired):
        return "PLATFORM_ADMIN"
    return error.permission.value


def journal_shop(actor: Actor, now: datetime) -> ShopId | None:
    """Boutique dont le journal reçoit le refus, ou `None` (journal plateforme)."""
    if actor.shop_id is None:
        return None
    if not actor.is_platform_admin:
        return actor.shop_id  # membre : rattachement actif relu par `actor_for`
    delegation = actor.delegation
    if delegation is not None and delegation.allows(actor.shop_id, now):
        return actor.shop_id
    return None


def denial_record(actor: Actor, permission: str, now: datetime) -> AuditRecord:
    return AuditRecord(
        performer=Performer(actor.user_id, role_label(actor), actor.device_id),
        action=AuditAction.ACCESS_DENIED,
        entity=EntityRef(ENTITY_TYPE, number=permission),
        module=MODULE,
        summary=f"Accès refusé : {permission}",
        captured_at=now,
    )


class RecordAccessDenied:
    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    def execute(self, error: AccessDenial) -> ShopId | None:
        """Inscrit le refus ; renvoie la boutique journalisée (`None` : journal plateforme)."""
        if not isinstance(error, ACCESS_DENIALS):
            msg = f"Refus d'accès attendu, reçu {type(error).__name__}"
            raise TypeError(msg)
        now = self._clock.now()
        actor = error.actor
        permission = _permission_code(error)
        shop_id = None if isinstance(error, PlatformAdminRequired) else journal_shop(actor, now)
        if shop_id is None:
            platform_log.warning(
                "Accès refusé user=%s role=%s device=%s shop=%s permission=%s",
                actor.user_id,
                role_label(actor),
                actor.device_id,
                actor.shop_id,
                permission,
            )
            return None
        entry = AuditEntry.inscribe(
            shop_id,
            denial_record(actor, permission, now),
            received_at=now,
            default_captured_at=now,
        )
        with self._uow_factory(shop_id) as uow:
            AuditLog.within(uow).append(entry)
            uow.commit()
        return shop_id
