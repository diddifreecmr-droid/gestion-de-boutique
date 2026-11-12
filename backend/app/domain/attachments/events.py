"""Événements des pièces jointes, journalisés (RG-T01, module « attachments »)."""

from dataclasses import dataclass

from app.domain.audit.values import AuditAction
from app.domain.shops.events import ShopAuditedEvent

ATTACHMENTS_MODULE = "attachments"


@dataclass(frozen=True, kw_only=True)
class AttachmentUploaded(ShopAuditedEvent):
    """Fichier envoyé et enregistré (type, élément lié, format, taille ; jamais le contenu)."""

    action = AuditAction.CREATE
    module = ATTACHMENTS_MODULE
