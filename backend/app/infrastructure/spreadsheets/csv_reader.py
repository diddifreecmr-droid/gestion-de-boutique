"""Lecture d'un `.csv` (IMP-06) : virgule ou point-virgule, UTF-8 avec ou sans BOM.

- Encodage : UTF-8 (BOM retiré) ; à défaut **Windows-1252**, celui de l'enregistrement
  « CSV (séparateur : point-virgule) » d'Excel en français. Octet nul (UTF-16, binaire) ou
  octet indéfini en Windows-1252 → `IMPORT_FILE_INVALID`.
- Séparateur : celui des deux qui revient le plus sur la première ligne non vide
  (point-virgule à égalité : les montants « 1 250,5 » n'y sont pas confondus).
- Lecture stricte : guillemet non refermé → `IMPORT_FILE_INVALID` (jamais de ligne devinée).
"""

import csv
import io

from app.domain.imports.errors import ImportFileInvalid
from app.domain.imports.sheet import Sheet
from app.infrastructure.spreadsheets.rows import build_sheet

UTF8_BOM = b"\xef\xbb\xbf"


def _decode(content: bytes) -> str:
    if b"\x00" in content:
        reason = "fichier illisible (enregistrer en .xlsx ou en CSV UTF-8)"
        raise ImportFileInvalid(reason)
    if content.startswith(UTF8_BOM):
        content = content[len(UTF8_BOM) :]
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:  # pas de l'UTF-8 : encodage d'Excel en français, sinon refus
        return _windows_1252(content)


def _windows_1252(content: bytes) -> str:
    try:
        return content.decode("cp1252")
    except UnicodeDecodeError as exc:
        reason = "encodage du fichier CSV non reconnu (UTF-8 attendu)"
        raise ImportFileInvalid(reason) from exc


def _delimiter(text: str) -> str:
    first = next((line for line in text.splitlines() if line.strip()), "")
    return "," if first.count(",") > first.count(";") else ";"


def read_csv(content: bytes) -> Sheet:
    text = _decode(content)
    try:
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=_delimiter(text), strict=True)
        rows = list(reader)
    except csv.Error as exc:
        reason = f"fichier CSV mal formé ({exc})"
        raise ImportFileInvalid(reason) from exc
    return build_sheet(rows)
