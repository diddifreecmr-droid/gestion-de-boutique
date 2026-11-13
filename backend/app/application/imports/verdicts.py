"""Aides communes aux modèles d'import (T33, T34) : verdict ligne par ligne, notes, valeurs.

- `RowRefused` : levée par le contrôle d'une ligne, rattrapée par le modèle (`Verdict.refuse`).
- `Verdict` : chaque ligne reçue est acceptée **ou** écartée (une seule fois) ; `check()` rend
  le `ModelCheck` de l'aperçu, `require_all_accepted()` garde l'écriture (`apply`) : une ligne
  qui ne passerait plus est une incohérence de l'appelant (`RuntimeError`), jamais ignorée.
- `require_first(seen, clé, colonne, libellé)` : doublon dans le fichier.
- `problem_of(error)` : message d'une erreur métier en phrase de ligne (« … est vide »).
- `created_note(n, singulier, pluriel)` : « 1 article nouveau sera créé », « 3 articles
  nouveaux seront créés » ; rien pour 0.
- `text`, `amount`, `number`, `day` : lecture typée d'une valeur nettoyée (`ParsedRow`) ; un
  type inattendu est une erreur de programmation (`TypeError`).
"""

from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal

from app.application.imports.models import ModelCheck
from app.domain.imports.problems import MESSAGE_MAX, RowError
from app.domain.imports.sheet import ParsedRow
from app.domain.shared.errors import DomainError


class RowRefused(Exception):
    """Ligne écartée pendant le contrôle : colonne en cause (`None` = toute la ligne), message."""

    def __init__(self, column: str | None, message: str) -> None:
        super().__init__(message)
        self.column = column
        self.message = message


class Verdict:
    def __init__(self) -> None:
        self._accepted: list[int] = []
        self._refused: list[RowError] = []
        self._judged: set[int] = set()

    def _judge(self, line: int) -> None:
        if line in self._judged:
            msg = f"Ligne {line} jugée deux fois"
            raise RuntimeError(msg)
        self._judged.add(line)

    def accept(self, line: int) -> None:
        self._judge(line)
        self._accepted.append(line)

    def refuse(self, line: int, column: str | None, message: str) -> None:
        self._judge(line)
        self._refused.append(RowError(line, column, message[:MESSAGE_MAX]))

    @property
    def accepted(self) -> tuple[int, ...]:
        return tuple(self._accepted)

    def check(self, *notes: str | None) -> ModelCheck:
        return ModelCheck(
            accepted=self.accepted,
            refused=tuple(self._refused),
            notes=tuple(note for note in notes if note),
        )

    def require_all_accepted(self, rows: Sequence[ParsedRow]) -> None:
        if self._refused or len(self._accepted) != len(rows):
            lines = [error.line for error in self._refused]
            msg = f"Import : lignes {lines} reçues pour écriture mais refusées par le modèle"
            raise RuntimeError(msg)


def require_first[K](seen: Mapping[K, int], key: K, column: str | None, label: str) -> None:
    """Doublon dans le fichier : « doublon : « Chemise » figure déjà ligne 2 »."""
    if key in seen:
        message = f"doublon : {label} figure déjà ligne {seen[key]}"
        raise RowRefused(column, message)


def problem_of(error: DomainError) -> str:
    message = error.message.strip()
    return message[:1].lower() + message[1:]


def created_note(count: int, singular: str, plural: str) -> str | None:
    if count == 0:
        return None
    return f"{count} {singular if count == 1 else plural}"


def _typed[T](row: ParsedRow, key: str, kind: type[T]) -> T | None:
    value = row.values.get(key)
    if value is None or isinstance(value, kind):
        return value
    msg = f"Colonne {key} : {kind.__name__} attendu, reçu {type(value).__name__}"
    raise TypeError(msg)


def text(row: ParsedRow, key: str) -> str | None:
    return _typed(row, key, str)


def required_text(row: ParsedRow, key: str) -> str:
    value = text(row, key)
    if value is None:
        msg = f"Colonne obligatoire {key} vide après nettoyage"
        raise RuntimeError(msg)
    return value


def amount(row: ParsedRow, key: str) -> int | None:
    return _typed(row, key, int)


def number(row: ParsedRow, key: str) -> Decimal | None:
    return _typed(row, key, Decimal)


def day(row: ParsedRow, key: str) -> date | None:
    return _typed(row, key, date)
