"""Erreurs de port construites par **tous** les adaptateurs de persistance (mémoire, SQL).

Même message, mêmes détails quel que soit l'adaptateur : la suite de contrats compare
`Duplicate.details["constraint"]`, et l'interface HTTP ne voit jamais la différence.
"""

from app.domain.shared.errors import Duplicate, VersionConflict

PRIMARY_KEY = "id"
"""Nom de contrainte rapporté pour un identifiant déjà pris (clé primaire, toutes boutiques)."""


def duplicate(table: str, constraint: str) -> Duplicate:
    return Duplicate("Valeur déjà utilisée", details={"table": table, "constraint": constraint})


def version_conflict(expected: int | None, current: int | None) -> VersionConflict:
    return VersionConflict(
        "L'élément a été modifié entre-temps",
        details={"expected_version": expected, "current_version": current},
    )
