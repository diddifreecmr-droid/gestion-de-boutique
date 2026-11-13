"""Nettoyage des montants saisis dans un tableur (IMP-07, RG-T07 : FCFA entiers, ≥ 0).

Acceptés, tous lus 1 250 000 :

- `1250000`, `1 250 000` (espace, espace insécable, espace fine insécable ou espace fine) ;
- `1250000 FCFA`, `1 250 000 F CFA`, `1250000 XAF`, `1250000 F` (unité en fin, casse libre) ;
- `1.250.000` (points de milliers, groupes de 3 chiffres exactement) ;
- `1250000,00` / `1250000.00` (zéros après la virgule, export courant d'Excel) ;
- une cellule numérique d'Excel (entier, ou décimal sans partie fractionnaire).

Refusés (`CellRejected`, rapportés « Ligne n : … ») : partie décimale non nulle (`12,5` →
« montant entier attendu »), signe moins, texte illisible, montant hors `BIGINT`.
"""

import re
from decimal import Decimal

from app.domain.imports.problems import CellRejected
from app.domain.shared.money import BIGINT_MAX

_SPACES = re.compile(r"[\s\N{NO-BREAK SPACE}\N{NARROW NO-BREAK SPACE}\N{THIN SPACE}]+")
_UNIT = re.compile(r"(?:FCFA|XAF|F)$", re.IGNORECASE)  # espaces déjà retirés : « F CFA »
_PLAIN = re.compile(r"^\d+$")
_DOTTED_THOUSANDS = re.compile(r"^\d{1,3}(?:\.\d{3})+$")
_ZERO_DECIMALS = re.compile(r"^(\d+)[.,]0+$")
_DECIMALS = re.compile(r"^\d+[.,]\d+$")

INTEGER_EXPECTED = "montant entier attendu (FCFA, sans centimes)"
NEGATIVE = "le montant ne peut pas être négatif"
UNREADABLE = "montant illisible"
TOO_LARGE = "montant trop grand"


def _bounded(value: int) -> int:
    if value < 0:
        raise CellRejected(NEGATIVE)
    if value > BIGINT_MAX:
        raise CellRejected(TOO_LARGE)
    return value


def _from_decimal(value: Decimal) -> int:
    if not value.is_finite():
        raise CellRejected(UNREADABLE)
    if value != value.to_integral_value():
        raise CellRejected(INTEGER_EXPECTED)
    return _bounded(int(value))


def _from_text(text: str) -> int:
    compact = _UNIT.sub("", _SPACES.sub("", text))
    if compact.startswith("-"):
        raise CellRejected(NEGATIVE)
    if _PLAIN.fullmatch(compact):
        return _bounded(int(compact))
    if _DOTTED_THOUSANDS.fullmatch(compact):
        return _bounded(int(compact.replace(".", "")))
    zero = _ZERO_DECIMALS.fullmatch(compact)
    if zero is not None:
        return _bounded(int(zero.group(1)))
    if _DECIMALS.fullmatch(compact):
        raise CellRejected(INTEGER_EXPECTED)
    raise CellRejected(UNREADABLE)


def parse_amount(value: object) -> int:
    """Montant en FCFA entiers ; la cellule vide est traitée par l'appelant (`columns.py`)."""
    if isinstance(value, bool):
        raise CellRejected(UNREADABLE)
    if isinstance(value, int):
        return _bounded(value)
    if isinstance(value, Decimal):
        return _from_decimal(value)
    if isinstance(value, float):  # un lecteur convertit déjà en Decimal : défense en profondeur
        return _from_decimal(Decimal(str(value)))  # « nan », « inf » : non finis, refusés
    if isinstance(value, str):
        return _from_text(value.strip())
    raise CellRejected(UNREADABLE)
