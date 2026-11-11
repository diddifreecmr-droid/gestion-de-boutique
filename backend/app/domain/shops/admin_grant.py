"""Agrégat `AdminAccessGrant` : le propriétaire autorise l'administrateur plateforme (§ 8.3).

Sans délégation active, l'administrateur ne voit rien de la boutique (404, CDC § 4.1). Une
délégation dure 24 h par défaut (décision Q7, specs § 15.1), **en lecture seule** (la `Policy`
refuse toute écriture). Le propriétaire peut la retirer avant son terme. Accorder une
délégation alors qu'une autre court la remplace (l'ancienne est retirée, la nouvelle repart
pour 24 h). Chaque accord et chaque retrait sont journalisés et signalés sensibles.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.domain.audit.values import EntityRef, FieldChange, Performer
from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import InvalidStateTransition
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId, UserId
from app.domain.shops.events import AdminAccessGranted, AdminAccessRevoked
from app.domain.shops.ids import AdminGrantId

DEFAULT_GRANT_DURATION = timedelta(hours=24)


@dataclass(eq=False, kw_only=True)
class AdminAccessGrant:
    id: AdminGrantId
    shop_id: ShopId
    granted_by: UserId
    granted_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    revoked_by: UserId | None = None
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.granted_at = require_aware(self.granted_at)
        self.expires_at = require_aware(self.expires_at)
        if self.expires_at <= self.granted_at:
            msg = "Une délégation expire après son accord"
            raise ValueError(msg)
        if self.revoked_at is not None:
            self.revoked_at = require_aware(self.revoked_at)

    @property
    def entity(self) -> EntityRef:
        return EntityRef("admin_access", self.id.value)

    def is_active(self, now: datetime) -> bool:
        return self.revoked_at is None and require_aware(now) < self.expires_at

    @classmethod
    def grant(
        cls,
        *,
        shop_id: ShopId,
        performer: Performer,
        now: datetime,
        duration: timedelta = DEFAULT_GRANT_DURATION,
    ) -> "AdminAccessGrant":
        if duration <= timedelta(0):
            msg = f"Durée de délégation strictement positive attendue, reçu {duration}"
            raise ValueError(msg)
        grant = cls(
            id=AdminGrantId.new(),
            shop_id=shop_id,
            granted_by=performer.user_id,
            granted_at=now,
            expires_at=require_aware(now) + duration,
        )
        grant.events.record(
            AdminAccessGranted(
                shop_id=shop_id,
                occurred_at=now,
                performer=performer,
                entity=grant.entity,
                summary="Accès accordé à l'administrateur plateforme",
                changes=(FieldChange("expires_at", None, grant.expires_at.isoformat()),),
            )
        )
        return grant

    def revoke(self, *, performer: Performer, now: datetime) -> None:
        if not self.is_active(now):
            msg = "Cette délégation n'est plus active"
            raise InvalidStateTransition(msg, details={"grant_id": str(self.id)})
        self.revoked_at = require_aware(now)
        self.revoked_by = performer.user_id
        self.events.record(
            AdminAccessRevoked(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary="Accès de l'administrateur plateforme retiré",
                changes=(FieldChange("revoked_at", None, self.revoked_at.isoformat()),),
            )
        )
