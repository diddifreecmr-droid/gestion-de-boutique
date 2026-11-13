"""Valeurs de l'import (TR-22, UC-IMP-01 à 03, décision client QC-6).

- **Modèles** (`ImportKind`, specs § 14 : 5 modèles au Lot 3) : articles, stock de départ,
  clients, créances en cours, fournisseurs. Les modèles Camions et Chauffeurs (Lot 2) n'existent
  pas : leur code est inconnu (404).
- **Fichier** : `.xlsx` ou `.csv` (virgule ou point-virgule), 5 Mo au plus, **5 000 lignes**
  de données au plus (`IMPORT_TOO_MANY_ROWS`).
- **Aperçu** valable 30 minutes (`IMPORT_PREVIEW_EXPIRED` au-delà).
- **Annulation** (QC-6) : possible pendant 7 jours calendaires **inclus** à partir de la date
  de l'import (journée de Douala) : importé le 10/11, annulable jusqu'au 17/11 compris.
"""

from datetime import timedelta
from enum import StrEnum

MAX_ROWS = 5_000
"""Lignes de données au plus par fichier (l'en-tête n'est pas comptée)."""
MAX_FILE_BYTES = 5 * 1024 * 1024
"""Taille d'un fichier d'import : 5 Mo au plus (bien au-delà de 5 000 lignes utiles)."""
PREVIEW_TTL = timedelta(minutes=30)
CANCEL_WINDOW_DAYS = 7


class ImportKind(StrEnum):
    """Modèle d'import (code stable de l'API : `GET /imports/templates/{kind}`)."""

    ARTICLES = "articles"
    OPENING_STOCK = "opening_stock"  # Stock de départ
    CUSTOMERS = "customers"
    RECEIVABLES = "receivables"  # Créances en cours
    SUPPLIERS = "suppliers"

    @property
    def label(self) -> str:
        return _KIND_LABELS[self]


_KIND_LABELS = {
    ImportKind.ARTICLES: "Articles",
    ImportKind.OPENING_STOCK: "Stock de départ",
    ImportKind.CUSTOMERS: "Clients",
    ImportKind.RECEIVABLES: "Créances en cours",
    ImportKind.SUPPLIERS: "Fournisseurs",
}


class ImportStatus(StrEnum):
    """Cycle de vie d'un lot (specs § 7) : `Importé → Annulé`."""

    IMPORTED = "imported"
    CANCELLED = "cancelled"


class SpreadsheetFormat(StrEnum):
    """Format reconnu aux octets ; valeur = type MIME."""

    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    CSV = "text/csv"

    @property
    def extension(self) -> str:
        return "xlsx" if self is SpreadsheetFormat.XLSX else "csv"


class ImportedEntity(StrEnum):
    """Type d'élément créé par un lot (tracé pour l'annulation, QC-6)."""

    ARTICLE = "article"
    STOCK_MOVEMENT = "stock_movement"
    CUSTOMER = "customer"
    RECEIVABLE = "receivable"
    SUPPLIER = "supplier"
