"""Événements de l'import, journalisés (RG-T01, AUD-L3-01 : « Importer », numéro `IMP-…`)."""

from dataclasses import dataclass

from app.domain.audit.values import AuditAction
from app.domain.shops.events import ShopAuditedEvent

IMPORT_MODULE = "import"


@dataclass(frozen=True, kw_only=True)
class ImportRecorded(ShopAuditedEvent):
    """Lot enregistré : modèle, lignes importées et ignorées (jamais le contenu du fichier)."""

    action = AuditAction.IMPORT
    module = IMPORT_MODULE


@dataclass(frozen=True, kw_only=True)
class ImportCancelled(ShopAuditedEvent):
    """Lot annulé (QC-6) : éléments archivés ou désactivés, rien d'effacé ; toujours sensible."""

    action = AuditAction.CANCEL
    module = IMPORT_MODULE
    sensitive = True
