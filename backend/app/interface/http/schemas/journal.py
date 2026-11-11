"""Schémas des routes du journal et des alertes (specs § 6.3, pagination § 6.1).

Le journal renvoie des **champs structurés** (auteur, rôle, action, élément, changements) et
un `summary` simple ; la phrase finale (« Paul (Vendeur) a enregistré la vente V-000124… »)
est composée par le frontend, qui connaît les noms et les libellés du profil.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EntityResponse(_Out):
    type: str
    id: str | None
    number: str | None


class PerformerResponse(_Out):
    user_id: str
    role: str
    device_id: str | None


class FieldChangeResponse(_Out):
    field: str
    before: str | int | bool | None
    after: str | int | bool | None


class AuditEntryResponse(_Out):
    id: str
    captured_at: datetime
    received_at: datetime
    performer: PerformerResponse
    action: str
    action_label: str
    module: str
    entity: EntityResponse
    summary: str
    changes: list[FieldChangeResponse]
    reason: str | None
    sensitive: bool


class AuditPageResponse(_Out):
    items: list[AuditEntryResponse]
    next_cursor: str | None


class AlertResponse(_Out):
    id: str
    type: str
    entity: EntityResponse
    message: str
    read: bool
    active: bool
    created_at: datetime


class AlertPageResponse(_Out):
    items: list[AlertResponse]
    next_cursor: str | None
    unread_count: int


class UnreadCountResponse(_Out):
    unread_count: int
