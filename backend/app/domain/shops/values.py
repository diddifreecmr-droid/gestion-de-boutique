"""Valeurs communes du socle : types de lieu, statuts, noms nettoyés et clés d'unicité.

Un nom saisi est nettoyé (espaces de bord retirés, espaces internes réduits à un seul) ; la
**clé d'unicité** (`name_key`) l'est en plus sans tenir compte de la casse : « Garoua » et
« garoua » sont le même lieu (CDC § 20.1 « unique dans la boutique »).
"""

from enum import StrEnum

from app.domain.shared.errors import ValidationFailed

NAME_MAX_LENGTH = 120
SHORT_TEXT_MAX_LENGTH = 200


class LocationKind(StrEnum):
    STORE = "store"
    """« Boutique » : peut être un point de vente."""
    WAREHOUSE = "warehouse"
    """« Entrepôt » : garde du stock."""


class ShopStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"
    """« Fermée » : ses membres n'y accèdent plus (404), ses données restent."""


class AccountStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


def clean_text(value: object, field: str, *, max_length: int = NAME_MAX_LENGTH) -> str:
    """Texte obligatoire, nettoyé ; `ValidationFailed` (champ nommé) s'il est vide ou trop long."""
    cleaned = " ".join(value.split()) if isinstance(value, str) else ""
    if not cleaned or len(cleaned) > max_length:
        msg = f"Texte obligatoire de {max_length} caractères au plus"
        raise ValidationFailed(msg, details={"field": field, "max_length": max_length})
    return cleaned


def clean_optional(
    value: object, field: str, *, max_length: int = SHORT_TEXT_MAX_LENGTH
) -> str | None:
    """Texte facultatif : `None` ou vide → `None`, sinon nettoyé et borné."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return clean_text(value, field, max_length=max_length)


def name_key(name: str) -> str:
    """Clé d'unicité d'un nom : nettoyé et sans casse (`casefold`)."""
    return " ".join(name.split()).casefold()


def require_int(value: object, field: str, *, low: int, high: int) -> int:
    """Entier borné `[low, high]` ; `ValidationFailed` sinon (un booléen n'est pas un entier)."""
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        msg = f"Entier entre {low} et {high} attendu"
        raise ValidationFailed(msg, details={"field": field, "min": low, "max": high})
    return value
