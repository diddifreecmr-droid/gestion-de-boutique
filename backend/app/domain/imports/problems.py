"""Problème d'une ligne du fichier : « Ligne 14 : le prix est vide » (UC-IMP-02, IMP-12).

- `line` : numéro de ligne **du tableur** (l'en-tête est la ligne 1, la première ligne de
  données la ligne 2) : l'utilisateur la retrouve telle quelle dans Excel.
- `column` : en-tête de la colonne en cause (`None` si le problème touche toute la ligne,
  comme un doublon).
- `CellRejected` : refus d'une cellule par un nettoyeur (`amounts.py`, `columns.py`) ; il est
  **toujours** rattrapé par la lecture du tableau et converti en `RowError` (la ligne est
  ignorée, jamais importée à moitié). Ce n'est pas une `DomainError` : il ne sort jamais du
  domaine tel quel.
"""

from dataclasses import dataclass

MESSAGE_MAX = 300


class CellRejected(Exception):
    """Cellule refusée ; `message` est une phrase française sans majuscule initiale."""

    def __init__(self, message: str) -> None:
        if not message.strip():
            msg = "Un refus de cellule exige un message"
            raise ValueError(msg)
        super().__init__(message)
        self.message = message


@dataclass(frozen=True, slots=True)
class RowError:
    line: int
    column: str | None
    message: str

    def __post_init__(self) -> None:
        if isinstance(self.line, bool) or not isinstance(self.line, int) or self.line < 2:
            msg = f"Ligne de données attendue (≥ 2), reçu {self.line!r}"
            raise ValueError(msg)
        if not self.message.strip() or len(self.message) > MESSAGE_MAX:
            msg = f"Message de ligne vide ou trop long (≤ {MESSAGE_MAX})"
            raise ValueError(msg)

    @property
    def sort_key(self) -> tuple[int, str, str]:
        return (self.line, self.column or "", self.message)

    @property
    def text(self) -> str:
        """Phrase affichée et reprise dans le rapport d'erreurs : « Ligne 14 : le prix… »."""
        return f"Ligne {self.line} : {self.message}"
