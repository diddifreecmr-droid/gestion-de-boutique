"""Colonnes d'un modèle d'import et nettoyage de leurs cellules (UC-IMP-01, UC-IMP-02).

Une colonne déclare son en-tête (« Prix de vente »), son **sujet** pour les messages (« le prix
de vente », d'où « Ligne 14 : le prix de vente est vide »), son type, son caractère obligatoire,
un exemple et une aide (feuille « Mode d'emploi »), et éventuellement la **liste** qui alimente
sa liste déroulante (`ChoiceSource` : lieux, catégories, types de client). La correspondance
d'une valeur de liste avec un objet de la boutique (lieu inconnu…) relève du modèle (T33, T34).

Cellule vide (`None` ou blanc) : `None` si la colonne est facultative, sinon « … est vide ».
"""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from app.domain.imports.amounts import parse_amount
from app.domain.imports.problems import CellRejected

_CODE = re.compile(r"^[a-z][a-z0-9_]*$")
_SPACES = re.compile(r"[\s\N{NO-BREAK SPACE}\N{NARROW NO-BREAK SPACE}\N{THIN SPACE}]+")
_FRENCH_DATE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
TEXT_MAX = 120

type CellValue = str | int | Decimal | date | bool | None
"""Valeur lue par un `SpreadsheetReader` (un `datetime` est une `date`)."""
type CleanValue = str | int | Decimal | date | None


class ColumnKind(StrEnum):
    TEXT = "text"
    AMOUNT = "amount"  # FCFA entiers ≥ 0 (`amounts.py`)
    NUMBER = "number"  # décimal ≥ 0 (« 2,5 » ou 2.5) : quantité, longueur
    DATE = "date"  # date d'Excel, « 31/10/2026 » ou « 2026-10-31 »


class ChoiceSource(StrEnum):
    """Liste déroulante du modèle, remplie avec les données de la boutique (`choices.py`)."""

    LOCATIONS = "locations"
    CATEGORIES = "categories"
    CUSTOMER_KINDS = "customer_kinds"


@dataclass(frozen=True, slots=True, kw_only=True)
class ColumnSpec:
    key: str
    header: str
    subject: str
    kind: ColumnKind = ColumnKind.TEXT
    required: bool = False
    example: str = ""
    help: str = ""
    choices: ChoiceSource | None = None
    max_length: int = TEXT_MAX

    def __post_init__(self) -> None:
        if not _CODE.fullmatch(self.key):
            msg = f"Clé de colonne en snake_case attendue, reçu {self.key!r}"
            raise ValueError(msg)
        if not self.header.strip() or not self.subject.strip():
            msg = f"Colonne {self.key} : en-tête et sujet obligatoires"
            raise ValueError(msg)
        object.__setattr__(self, "kind", ColumnKind(self.kind))

    @property
    def title(self) -> str:
        """En-tête écrit dans le modèle : « Nom * » pour une colonne obligatoire."""
        return f"{self.header} *" if self.required else self.header

    def clean(self, value: CellValue) -> CleanValue:
        """Valeur nettoyée ; `CellRejected` avec un message complet sinon."""
        if value is None or (isinstance(value, str) and not value.strip()):
            if self.required:
                problem = f"{self.subject} est vide"
                raise CellRejected(problem)
            return None
        try:
            return _CLEANERS[self.kind](self, value)
        except CellRejected as exc:
            problem = f"{self.subject} : {exc.message}"
            raise CellRejected(problem) from exc


def _text(column: ColumnSpec, value: CellValue) -> str:
    if isinstance(value, date):
        text = value.strftime("%d/%m/%Y")
    elif isinstance(value, Decimal):
        text = format(value.normalize(), "f")
    else:
        text = str(value)
    text = " ".join(text.split())
    if len(text) > column.max_length:
        problem = f"{column.max_length} caractères au plus"
        raise CellRejected(problem)
    return text


def _amount(_: ColumnSpec, value: CellValue) -> int:
    return parse_amount(value)


def _number(_: ColumnSpec, value: CellValue) -> Decimal:
    if isinstance(value, bool | date):
        problem = "nombre illisible"
        raise CellRejected(problem)
    if isinstance(value, int | Decimal):
        number = Decimal(value)
    else:
        try:
            number = Decimal(_SPACES.sub("", str(value)).replace(",", "."))
        except InvalidOperation as exc:
            problem = "nombre illisible"
            raise CellRejected(problem) from exc
    if not number.is_finite():
        problem = "nombre illisible"
        raise CellRejected(problem)
    if number < 0:
        problem = "le nombre ne peut pas être négatif"
        raise CellRejected(problem)
    return number


def _date(_: ColumnSpec, value: CellValue) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    french = _FRENCH_DATE.fullmatch(text)
    try:
        if french is not None:
            day, month, year = (int(part) for part in french.groups())
            return date(year, month, day)
        return date.fromisoformat(text)
    except ValueError as exc:
        problem = "date illisible (attendu 31/10/2026)"
        raise CellRejected(problem) from exc


_CLEANERS: Mapping[ColumnKind, Callable[[ColumnSpec, CellValue], CleanValue]] = {
    ColumnKind.TEXT: _text,
    ColumnKind.AMOUNT: _amount,
    ColumnKind.NUMBER: _number,
    ColumnKind.DATE: _date,
}
