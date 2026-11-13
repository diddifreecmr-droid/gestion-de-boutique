"""Erreurs de l'import (specs § 6.2, recette Lot 3 ERR3-04 à ERR3-08).

| Code | Statut | Détails |
| --- | --- | --- |
| `IMPORT_FILE_INVALID` | 400 | `reason` lisible (format, feuille vide, colonne absente…) |
| `IMPORT_TOO_MANY_ROWS` | 422 | `max` (5 000), `rows` (lignes lues) |
| `IMPORT_PREVIEW_EXPIRED` | 410 | `preview_id` |
| `IMPORT_CANCEL_TOO_LATE` | 422 | `imported_on`, `last_day` |
| `IMPORT_CANCEL_BLOCKED` | 422 | `blocking` : `[{type, number}]`, les opérations qui bloquent |

Une erreur **de ligne** (« Ligne 14 : le prix est vide ») n'est pas une exception : elle est
rapportée dans l'aperçu (`RowError`), la ligne est ignorée et les autres sont importées.
"""

from collections.abc import Sequence
from datetime import date

from app.domain.imports.blocking import BlockingOperation
from app.domain.imports.values import MAX_ROWS
from app.domain.shared.errors import DomainError, ValidationFailed


class ImportFileInvalid(ValidationFailed):
    """Fichier illisible, format refusé (`.xls`), feuille vide, colonne obligatoire absente."""

    code = "IMPORT_FILE_INVALID"

    def __init__(self, reason: str) -> None:
        super().__init__(f"Fichier refusé : {reason}", details={"reason": reason})


class ImportTooManyRows(DomainError):
    """Plus de 5 000 lignes de données (→ 422)."""

    code = "IMPORT_TOO_MANY_ROWS"

    def __init__(self, rows: int) -> None:
        super().__init__(
            f"Trop de lignes : {rows} lues, {MAX_ROWS} au plus par fichier",
            details={"max": MAX_ROWS, "rows": rows},
        )


class ImportPreviewExpired(DomainError):
    """Aperçu de plus de 30 minutes : recharger le fichier (→ 410)."""

    code = "IMPORT_PREVIEW_EXPIRED"

    def __init__(self, preview_id: str) -> None:
        super().__init__("Aperçu expiré : recharger le fichier", details={"preview_id": preview_id})


class ImportCancelTooLate(DomainError):
    """Annulation au-delà des 7 jours calendaires (QC-6, → 422)."""

    code = "IMPORT_CANCEL_TOO_LATE"

    def __init__(self, imported_on: date, last_day: date) -> None:
        super().__init__(
            f"Annulation impossible : possible jusqu'au {last_day.strftime('%d/%m/%Y')}",
            details={"imported_on": imported_on.isoformat(), "last_day": last_day.isoformat()},
        )


class ImportCancelBlocked(DomainError):
    """Une opération touche un élément du lot : vente, achat, versement… (QC-6, → 422)."""

    code = "IMPORT_CANCEL_BLOCKED"

    def __init__(self, blocking: Sequence[BlockingOperation]) -> None:
        if not blocking:
            msg = "Un refus d'annulation cite au moins une opération"
            raise ValueError(msg)
        listed = ", ".join(op.number for op in blocking[:5])
        more = "…" if len(blocking) > 5 else ""
        super().__init__(
            f"Annulation impossible : des opérations s'appuient sur ce lot ({listed}{more})",
            details={"blocking": [op.as_detail() for op in blocking]},
        )
