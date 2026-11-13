"""Lecture d'un `.xlsx` avec `openpyxl` (lecture seule, valeurs calculées).

- Feuille lue : la première feuille de calcul qui n'est ni « Mode d'emploi » ni « Listes »
  (celles du modèle téléchargé) ; aucune → `IMPORT_FILE_INVALID`.
- Archive corrompue, classeur protégé ou chiffré, parties manquantes → `IMPORT_FILE_INVALID`
  « fichier Excel illisible », avec la cause technique dans le journal du serveur.
- Les avertissements d'`openpyxl` sur des extensions non lues (mise en forme conditionnelle,
  validations avancées) ne concernent pas les valeurs : ils sont écartés pendant la lecture.
"""

import io
import logging
import warnings
import zipfile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from app.domain.imports.errors import ImportFileInvalid
from app.domain.imports.sheet import Sheet, fold_header
from app.infrastructure.spreadsheets.rows import build_sheet

logger = logging.getLogger(__name__)

HELP_SHEETS = frozenset({fold_header("Mode d'emploi"), fold_header("Listes")})
_UNREADABLE = (zipfile.BadZipFile, InvalidFileException, KeyError, ValueError, OSError, TypeError)


def read_xlsx(content: bytes) -> Sheet:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except _UNREADABLE as exc:
        logger.info("Import : classeur illisible (%s : %s)", type(exc).__name__, exc)
        reason = "fichier Excel illisible"
        raise ImportFileInvalid(reason) from exc
    try:
        sheets = [ws for ws in workbook.worksheets if fold_header(ws.title) not in HELP_SHEETS]
        if not sheets:
            reason = "aucune feuille de saisie dans le classeur"
            raise ImportFileInvalid(reason)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            return build_sheet(sheets[0].iter_rows(min_row=1, values_only=True))
    except _UNREADABLE as exc:
        logger.info("Import : feuille illisible (%s : %s)", type(exc).__name__, exc)
        reason = "fichier Excel illisible"
        raise ImportFileInvalid(reason) from exc
    finally:
        workbook.close()
