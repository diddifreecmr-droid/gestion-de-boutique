"""Erreurs métier typées (specs.md § 6.2, TR-25).

Chaque erreur porte un **code stable** (contrat de l'API, jamais traduit), un message lisible
et des détails structurés. L'interface HTTP choisit le statut à partir du *type* de l'erreur ;
le domaine ignore tout du transport.
"""

import re
from collections.abc import Mapping
from types import MappingProxyType
from typing import ClassVar

_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$")


class DomainError(Exception):
    """Base abstraite : ne se lève jamais directement, toujours via une sous-classe typée."""

    code: ClassVar[str]

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        code = cls.__dict__.get("code")
        if code is None:
            return  # sous-classe intermédiaire : hérite du code de son parent
        if not isinstance(code, str) or not _CODE_PATTERN.fullmatch(code):
            msg = f"{cls.__name__}.code doit être en MAJUSCULES_SNAKE_CASE, reçu {code!r}"
            raise TypeError(msg)

    def __init__(self, message: str, *, details: Mapping[str, object] | None = None) -> None:
        if type(self) is DomainError:
            msg = "DomainError est abstraite : lever une sous-classe typée"
            raise TypeError(msg)
        if not hasattr(type(self), "code"):
            msg = f"{type(self).__name__} doit définir un attribut de classe `code`"
            raise TypeError(msg)
        if not message.strip():
            msg = "Une DomainError exige un message non vide"
            raise ValueError(msg)
        super().__init__(message)
        self.message = message
        self.details: Mapping[str, object] = MappingProxyType(dict(details or {}))

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, message={self.message!r})"


class ValidationFailed(DomainError):
    """Donnée invalide au regard d'une règle du domaine."""

    code = "VALIDATION_ERROR"


class NotFound(DomainError):
    """Inexistant **ou** appartenant à une autre boutique (pas de fuite d'existence)."""

    code = "NOT_FOUND"


class Forbidden(DomainError):
    """Permission absente pour l'acteur courant."""

    code = "FORBIDDEN"


class Conflict(DomainError):
    """Conflit d'état générique ; préférer les sous-classes fines ci-dessous (→ HTTP 409)."""

    code = "CONFLICT"


# --------------------------------------------------------------- catalogue fin (§ 6.2)
class InvalidAmount(ValidationFailed):
    """Montant refusé : négatif dans un champ de saisie (RG-T07) ou hors bornes `BIGINT`."""

    code = "INVALID_AMOUNT"


class InvalidQuantity(ValidationFailed):
    """Quantité refusée : plus d'une décimale, décimale sur une unité entière (RG-T08)…"""

    code = "INVALID_QUANTITY"


class InvalidIdentifier(ValidationFailed):
    """Identifiant ou numéro de document mal formé (UUIDv7, `V-000124`, `V-HL-3F2A-0007`)."""

    code = "INVALID_IDENTIFIER"


class VersionConflict(Conflict):
    """L'objet a changé depuis sa lecture (verrou optimiste, specs § 6.1)."""

    code = "VERSION_CONFLICT"


class Duplicate(Conflict):
    """Violation d'unicité métier (téléphone, châssis, marque + modèle…)."""

    code = "DUPLICATE"


class DateOutOfRange(DomainError):
    """Date d'enregistrement hors de la fenêtre autorisée (RG-T09) → HTTP 422."""

    code = "DATE_OUT_OF_RANGE"


class InvalidStateTransition(DomainError):
    """Transition interdite par le cycle de vie de l'agrégat (specs § 7.1) → HTTP 422."""

    code = "INVALID_STATE_TRANSITION"
