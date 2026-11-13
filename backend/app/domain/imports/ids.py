"""Identifiants typés de l'import (UUIDv7, specs D5)."""

from app.domain.shared.ids import EntityId


class ImportBatchId(EntityId):
    """Lot d'import (`IMP-000001`)."""

    __slots__ = ()


class ImportPreviewId(EntityId):
    """Aperçu d'un fichier déposé, valable 30 minutes ; repris par la confirmation (T33)."""

    __slots__ = ()
