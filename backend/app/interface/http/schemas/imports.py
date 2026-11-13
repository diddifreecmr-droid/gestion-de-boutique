"""Schémas de l'import (UC-IMP-02) : aperçu ligne par ligne, sans écriture.

Jamais de clé de stockage ni de lien vers le fichier déposé (SEC-N3-03).
"""

from datetime import datetime

from pydantic import BaseModel

from app.domain.imports.values import ImportKind


class ImportProblemResponse(BaseModel):
    line: int
    """Numéro de ligne du tableur (l'en-tête est la ligne 1)."""
    column: str | None
    message: str
    text: str
    """Phrase à afficher : « Ligne 14 : le prix est vide »."""


class ImportPreviewResponse(BaseModel):
    preview_id: str
    """À reprendre pour confirmer l'import (`POST /imports`), avant `expires_at`."""
    kind: ImportKind
    expires_at: datetime
    rows_read: int
    rows_valid: int
    rows_ignored: int
    problems: list[ImportProblemResponse]
    """1 000 au plus ; `problems_total` donne le nombre exact."""
    problems_total: int
    notes: list[str]
    """Ce que l'import créerait : « 3 articles nouveaux seront créés »."""
