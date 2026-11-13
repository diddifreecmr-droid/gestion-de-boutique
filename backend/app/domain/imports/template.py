"""Description d'un modèle d'import : colonnes et mode d'emploi (UC-IMP-01, IMP-01).

Le modèle `.xlsx` téléchargé en découle (`SpreadsheetWriter`) : une feuille de saisie nommée
d'après le modèle (« Articles »), l'en-tête des colonnes (« Nom * » si obligatoire), des listes
déroulantes, et une feuille « Mode d'emploi » (consignes, une ligne par colonne, exemple).
"""

from dataclasses import dataclass

from app.domain.imports.columns import ColumnSpec
from app.domain.imports.sheet import fold_header
from app.domain.imports.values import MAX_ROWS, ImportKind

GENERAL_INSTRUCTIONS = (
    "Remplissez une ligne par élément, à partir de la ligne 2 de la feuille de saisie.",
    "Les colonnes marquées d'un astérisque (*) sont obligatoires.",
    "Montants en FCFA entiers : « 1 250 000 » ou « 1250000 FCFA » conviennent.",
    f"{MAX_ROWS} lignes au plus par fichier ; formats acceptés : .xlsx ou .csv.",
    "Avant tout enregistrement, l'application montre un aperçu ligne par ligne :"
    " les lignes en erreur sont signalées et ne sont pas importées.",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class TemplateSpec:
    kind: ImportKind
    columns: tuple[ColumnSpec, ...]
    instructions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", ImportKind(self.kind))
        if not self.columns:
            msg = f"Modèle {self.kind} sans colonne"
            raise ValueError(msg)
        keys = [column.key for column in self.columns]
        headers = [fold_header(column.header) for column in self.columns]
        if len(set(keys)) != len(keys) or len(set(headers)) != len(headers):
            msg = f"Modèle {self.kind} : clés ou en-têtes de colonne en double"
            raise ValueError(msg)

    @property
    def sheet_title(self) -> str:
        """Nom de la feuille de saisie (≤ 31 caractères, contrainte d'Excel)."""
        return self.kind.label

    @property
    def all_instructions(self) -> tuple[str, ...]:
        return (*GENERAL_INSTRUCTIONS, *self.instructions)
