"""Champs propres à un profil : détails d'un article et détails notés à la vente (specs § 4.5).

Ils décrivent le formulaire au frontend (`GET /shops/{id}/profile`) ; leur validation métier
arrive avec le catalogue (T13) et les ventes (T16), à partir de ces mêmes descriptions.
"""

from dataclasses import dataclass
from enum import StrEnum


class FieldKind(StrEnum):
    TEXT = "text"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    CHOICE = "choice"


@dataclass(frozen=True, slots=True)
class FieldSpec:
    code: str
    label: str
    kind: FieldKind
    required: bool = False
    unique: bool = False
    """Unique dans la boutique (ex. châssis, référence) : colonne indexée côté SQL."""
    choices: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (self.kind is FieldKind.CHOICE) != bool(self.choices):
            msg = f"Champ {self.code} : une liste de choix va avec le type « choice »"
            raise ValueError(msg)
