"""`SpreadsheetReader` : format reconnu **aux octets**, jamais au nom du fichier (IMP-05).

| Premiers octets | Format |
| --- | --- |
| `PK\\x03\\x04` (archive ZIP) | `.xlsx` (`openpyxl`) |
| `\\xd0\\xcf\\x11\\xe0…` (OLE) | `.xls` d'Excel 97-2003 : refusé, `IMPORT_FILE_INVALID` |
| `%PDF`, images | refusés |
| autre | texte CSV (virgule ou point-virgule) |
"""

from app.application.imports.ports import SpreadsheetReader
from app.domain.imports.errors import ImportFileInvalid
from app.domain.imports.sheet import Sheet
from app.domain.imports.values import SpreadsheetFormat
from app.infrastructure.spreadsheets.csv_reader import read_csv
from app.infrastructure.spreadsheets.xlsx_reader import read_xlsx

ZIP_SIGNATURE = b"PK\x03\x04"
OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_NOT_SPREADSHEETS = (b"%PDF", b"\xff\xd8\xff", b"\x89PNG", b"GIF8")


class TabularReader(SpreadsheetReader):
    def read(self, content: bytes) -> tuple[SpreadsheetFormat, Sheet]:
        if content.startswith(ZIP_SIGNATURE):
            return SpreadsheetFormat.XLSX, read_xlsx(content)
        if content.startswith(OLE_SIGNATURE):
            reason = "format .xls (Excel 97-2003) non pris en charge : enregistrer en .xlsx"
            raise ImportFileInvalid(reason)
        if content.startswith(_NOT_SPREADSHEETS):
            reason = "ce n'est pas un tableur (.xlsx ou .csv attendu)"
            raise ImportFileInvalid(reason)
        return SpreadsheetFormat.CSV, read_csv(content)
