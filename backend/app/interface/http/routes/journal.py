"""Routes du journal (UC-JRN-01 à 03) et des alertes (UC-SOC-09) — specs § 6.3.

Toutes sous `/shops/{shop_id}/…` : l'`Actor` est reconstruit à chaque requête par
`AuthGuard.current_actor` (rattachement relu). Un refus lève `PermissionDenied`, journalisé
par le gestionnaire d'erreurs (RG-D01). Pagination : `?cursor=&limit=` → `next_cursor`.
"""

from dataclasses import dataclass
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.application.alerts.use_cases.my_alerts import ListAlerts, MarkAlertRead
from app.application.audit.access_denied import RecordAccessDenied
from app.application.audit.use_cases.consult import ConsultAudit, JournalFilters
from app.application.ports.pagination import MAX_LIMIT, Page, PageRequest
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.domain.alerts.alert import AlertId
from app.domain.audit.entry import AuditEntry
from app.domain.audit.values import AuditAction
from app.domain.shared.ids import UserId
from app.interface.http.presenters.journal import alert_response, audit_entry_response
from app.interface.http.schemas.journal import (
    AlertPageResponse,
    AuditPageResponse,
    UnreadCountResponse,
)
from app.interface.http.security import AuthGuard


@dataclass(frozen=True, slots=True, kw_only=True)
class JournalComponents:
    """Cas d'utilisation assemblés par la composition root."""

    consult_audit: ConsultAudit
    list_alerts: ListAlerts
    mark_alert_read: MarkAlertRead
    record_access_denied: RecordAccessDenied
    policy: Policy
    guard: AuthGuard


Cursor = Annotated[str | None, Query(max_length=256)]
Limit = Annotated[int | None, Query(ge=1, le=MAX_LIMIT)]


def build_journal_router(journal: JournalComponents) -> APIRouter:
    router = APIRouter(tags=["journal"])
    CurrentActor = Annotated[Actor, Depends(journal.guard.current_actor)]  # noqa: N806

    def audit_page(actor: Actor, page: Page[AuditEntry]) -> AuditPageResponse:
        with_changes = journal.policy.can_read_field(actor, Permission.AUDIT_READ)
        return AuditPageResponse(
            items=[audit_entry_response(e, with_changes=with_changes) for e in page.items],
            next_cursor=None if page.next_cursor is None else page.next_cursor.encode(),
        )

    @router.get("/shops/{shop_id}/audit")
    def journal_list(
        actor: CurrentActor,
        first_day: Annotated[date | None, Query(alias="from")] = None,
        last_day: Annotated[date | None, Query(alias="to")] = None,
        user_id: Annotated[str | None, Query(max_length=64)] = None,
        action: Annotated[list[AuditAction] | None, Query()] = None,
        module: Annotated[list[str] | None, Query(max_length=64)] = None,
        cursor: Cursor = None,
        limit: Limit = None,
    ) -> AuditPageResponse:
        filters = JournalFilters(
            first_day=first_day,
            last_day=last_day,
            user_id=None if user_id is None else UserId.parse(user_id),
            actions=frozenset(action or ()),
            modules=frozenset(module or ()),
        )
        page = journal.consult_audit.journal(actor, filters, PageRequest.parse(cursor, limit))
        return audit_page(actor, page)

    @router.get("/shops/{shop_id}/audit/entities/{entity_type}/{entity_id}")
    def entity_history(
        actor: CurrentActor,
        entity_type: str,
        entity_id: UUID,
        cursor: Cursor = None,
        limit: Limit = None,
    ) -> AuditPageResponse:
        request = PageRequest.parse(cursor, limit)
        page = journal.consult_audit.entity_history(actor, entity_type, entity_id, request)
        return audit_page(actor, page)

    @router.get("/shops/{shop_id}/audit/users/{user_id}")
    def user_activity(
        actor: CurrentActor, user_id: str, cursor: Cursor = None, limit: Limit = None
    ) -> AuditPageResponse:
        request = PageRequest.parse(cursor, limit)
        page = journal.consult_audit.user_activity(actor, UserId.parse(user_id), request)
        return audit_page(actor, page)

    @router.get("/shops/{shop_id}/alerts")
    def list_alerts(
        actor: CurrentActor,
        unread_only: bool = False,
        cursor: Cursor = None,
        limit: Limit = None,
    ) -> AlertPageResponse:
        request = PageRequest.parse(cursor, limit)
        found = journal.list_alerts.execute(actor, request, unread_only=unread_only)
        nxt = found.page.next_cursor
        return AlertPageResponse(
            items=[alert_response(alert) for alert in found.page.items],
            next_cursor=None if nxt is None else nxt.encode(),
            unread_count=found.unread_count,
        )

    @router.post("/shops/{shop_id}/alerts/{alert_id}/read")
    def mark_alert_read(actor: CurrentActor, alert_id: str) -> UnreadCountResponse:
        remaining = journal.mark_alert_read.execute(actor, AlertId.parse(alert_id))
        return UnreadCountResponse(unread_count=remaining)

    return router
