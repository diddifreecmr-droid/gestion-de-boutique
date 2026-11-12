"""Valeurs des pièces jointes : type de document, élément lié, format de fichier (RG-T26).

- Formats admis : JPG, PNG ou PDF, **5 Mo au plus** (RG-T26). Le format est reconnu à la
  **signature des premiers octets**, jamais au nom ni au type annoncé par le client : un GIF,
  une page HTML ou un exécutable renommé en `.jpg` est refusé (`VALIDATION_ERROR`, 400).
- Élément lié (CDC § 20.5 « Pièce jointe ») : la visibilité **hérite** des droits de cet élément.
  La pièce d'identité d'un garant est rattachée à la créance qu'il garantit (`receivable`).
- Une pièce d'identité (`id_document`) n'est admise que sur un client ou une créance : ce sont
  les seuls éléments dont la photo est réservée au propriétaire et au vendeur responsable
  (UC-CRE-07, SEC-N06).
"""

from enum import StrEnum

from app.domain.shared.errors import ValidationFailed

MAX_SIZE_BYTES = 5 * 1024 * 1024
"""RG-T26 : 5 Mo au plus par fichier (5 242 880 octets ; 1 octet de plus est refusé)."""


class AttachmentKind(StrEnum):
    """Type de pièce jointe (CDC § 20.5)."""

    ID_DOCUMENT = "id_document"  # Pièce d'identité
    CONTRACT = "contract"  # Contrat
    DEBT_ACKNOWLEDGEMENT = "debt_acknowledgement"  # Reconnaissance de dette
    INVOICE = "invoice"  # Facture
    RECEIPT = "receipt"  # Justificatif
    PHOTO = "photo"
    OTHER = "other"


class OwnerType(StrEnum):
    """Élément auquel la pièce est rattachée ; il fixe les droits de lecture et d'envoi."""

    CUSTOMER = "customer"
    RECEIVABLE = "receivable"  # créance, ses garants compris
    ARTICLE = "article"
    EXPENSE = "expense"
    PURCHASE = "purchase"
    STOCK_ADJUSTMENT = "stock_adjustment"

    @property
    def is_personal(self) -> bool:
        """Données personnelles : l'élément lié est obligatoire et vérifié (portée « Siens »)."""
        return self in PERSONAL_OWNERS


PERSONAL_OWNERS = frozenset({OwnerType.CUSTOMER, OwnerType.RECEIVABLE})


class FileFormat(StrEnum):
    """Format reconnu : valeur = type MIME servi au navigateur."""

    JPEG = "image/jpeg"
    PNG = "image/png"
    PDF = "application/pdf"

    @property
    def extension(self) -> str:
        return _EXTENSIONS[self]


_EXTENSIONS = {FileFormat.JPEG: "jpg", FileFormat.PNG: "png", FileFormat.PDF: "pdf"}
_SIGNATURES = (
    (b"\xff\xd8\xff", FileFormat.JPEG),
    (b"\x89PNG\r\n\x1a\n", FileFormat.PNG),
    (b"%PDF-", FileFormat.PDF),
)


def detect_format(content: bytes) -> FileFormat:
    """Format lu dans les premiers octets ; `ValidationFailed` hors JPG, PNG et PDF."""
    for signature, file_format in _SIGNATURES:
        if content.startswith(signature):
            return file_format
    msg = "Format refusé : photo JPG ou PNG, ou document PDF"
    raise ValidationFailed(
        msg, details={"field": "file", "accepted": [f.value for f in FileFormat]}
    )


def require_size(size: int) -> int:
    """Taille en octets, de 1 à `MAX_SIZE_BYTES` ; `ValidationFailed` sinon (RG-T26)."""
    if isinstance(size, bool) or not isinstance(size, int):
        msg = "La taille d'un fichier est un entier d'octets"
        raise TypeError(msg)
    if size < 1:
        msg = "Fichier vide"
        raise ValidationFailed(msg, details={"field": "file"})
    if size > MAX_SIZE_BYTES:
        msg = "Fichier trop lourd : 5 Mo au plus"
        raise ValidationFailed(msg, details={"field": "file", "max_bytes": MAX_SIZE_BYTES})
    return size


def require_kind_allowed(kind: AttachmentKind, owner_type: OwnerType) -> None:
    """Une pièce d'identité ne se rattache qu'à un client ou à une créance (SEC-N06)."""
    if kind is AttachmentKind.ID_DOCUMENT and not owner_type.is_personal:
        msg = "Une pièce d'identité se rattache à un client ou à une créance"
        raise ValidationFailed(msg, details={"field": "kind", "owner_type": owner_type.value})
