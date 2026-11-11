"""UC-JRN-01 à 03 — consulter le journal, l'historique d'un élément, l'activité d'un utilisateur.

Droit : `AUDIT_READ` (CDC § 4.2 : propriétaire seul ; l'administrateur avec délégation consulte
en lecture). Un refus lève `PermissionDenied`, journalisé par l'interface (RG-D01). Lecture
seule : l'unité de travail n'écrit rien et n'a pas besoin de `commit()`.

Période (`first_day`/`last_day`) : journées `Africa/Douala` incluses (specs § 6.1), appliquées
à l'heure de l'action.
"""

from collections.abc import Set
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from app.application.audit.ports import AuditLog, AuditQuery
from app.application.ports.pagination import Page, PageRequest
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.domain.audit.entry import AuditEntry
from app.domain.audit.values import AuditAction, require_code
from app.domain.shared.business_day import period_bounds_utc
from app.domain.shared.ids import ShopId, UserId


@dataclass(frozen=True, slots=True, kw_only=True)
class JournalFilters:
    """Filtres de UC-JRN-01 : période, utilisateur, type d'action, module."""

    first_day: date | None = None
    last_day: date | None = None
    user_id: UserId | None = None
    actions: Set[AuditAction] = field(default_factory=frozenset)
    modules: Set[str] = field(default_factory=frozenset)

    def to_query(self) -> AuditQuery:
        since = until = None
        given = [day for day in (self.first_day, self.last_day) if day is not None]
        if given:  # une seule borne fournie : la période se réduit à ce jour
            since, until = period_bounds_utc(self.first_day or given[0], self.last_day or given[0])
        for module in self.modules:
            require_code(module, "module")
        return AuditQuery(
            since=since,
            until=until,
            user_id=self.user_id,
            actions=self.actions,
            modules=self.modules,
        )


class ConsultAudit:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy) -> None:
        self._uow_factory = uow_factory
        self._policy = policy

    def journal(self, actor: Actor, filters: JournalFilters, page: PageRequest) -> Page[AuditEntry]:
        """UC-JRN-01 : liste chronologique filtrée, la plus récente en haut."""
        return self._search(actor, filters.to_query(), page)

    def entity_history(
        self, actor: Actor, entity_type: str, entity_id: UUID, page: PageRequest
    ) -> Page[AuditEntry]:
        """UC-JRN-02 : changements successifs d'un élément (onglet « Historique »)."""
        require_code(entity_type, "entity_type")
        return self._search(actor, AuditQuery(entity_type=entity_type, entity_id=entity_id), page)

    def user_activity(self, actor: Actor, user_id: UserId, page: PageRequest) -> Page[AuditEntry]:
        """UC-JRN-03 : actions et connexions d'un utilisateur dans cette boutique."""
        return self._search(actor, AuditQuery(user_id=user_id), page)

    def _search(self, actor: Actor, query: AuditQuery, page: PageRequest) -> Page[AuditEntry]:
        shop_id = self._authorize(actor)
        with self._uow_factory(shop_id) as uow:
            return AuditLog.within(uow).search(query, page)

    def _authorize(self, actor: Actor) -> ShopId:
        self._policy.require(actor, Permission.AUDIT_READ)
        if actor.shop_id is None:  # exclu par la Policy (admin hors boutique) : défense
            msg = "Consultation du journal sans boutique"
            raise RuntimeError(msg)
        return actor.shop_id
