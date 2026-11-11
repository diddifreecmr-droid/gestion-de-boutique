"""Présentation des entrées de journal et des alertes.

Journal : la route exige déjà `AUDIT_READ` ; les valeurs avant/après ne sont incluses que si
`Policy.can_read_field(actor, AUDIT_READ)` (défense en profondeur, TR-05). Alertes : chacun ne
reçoit que les siennes ; leur message est rédigé par la règle du module, sans donnée interdite
à son destinataire (responsabilité de la règle, testée avec elle).
"""

from app.domain.alerts.alert import Alert
from app.domain.audit.entry import AuditEntry
from app.domain.audit.values import EntityRef
from app.interface.http.schemas.journal import (
    AlertResponse,
    AuditEntryResponse,
    EntityResponse,
    FieldChangeResponse,
    PerformerResponse,
)


def entity_response(entity: EntityRef) -> EntityResponse:
    return EntityResponse(
        type=entity.type,
        id=None if entity.id is None else str(entity.id),
        number=entity.number,
    )


def audit_entry_response(entry: AuditEntry, *, with_changes: bool) -> AuditEntryResponse:
    device = entry.performer.device_id
    return AuditEntryResponse(
        id=str(entry.id),
        captured_at=entry.captured_at,
        received_at=entry.received_at,
        performer=PerformerResponse(
            user_id=str(entry.performer.user_id),
            role=entry.performer.role,
            device_id=None if device is None else str(device),
        ),
        action=entry.action.value,
        action_label=entry.action.label,
        module=entry.module,
        entity=entity_response(entry.entity),
        summary=entry.summary,
        changes=[
            FieldChangeResponse(field=c.field, before=c.before, after=c.after)
            for c in entry.changes
        ]
        if with_changes
        else [],
        reason=entry.reason,
        sensitive=entry.sensitive,
    )


def alert_response(alert: Alert) -> AlertResponse:
    return AlertResponse(
        id=str(alert.id),
        type=alert.type.value,
        entity=entity_response(alert.entity),
        message=alert.message,
        read=alert.read,
        active=alert.active,
        created_at=alert.created_at,
    )
