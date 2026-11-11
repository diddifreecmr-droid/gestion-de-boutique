"""Refus propres à la synchronisation hors connexion (codes stables, specs § 6.2 et § 6.5)."""

from app.domain.shared.errors import DomainError, ValidationFailed


class OperationNotAllowedOffline(DomainError):
    """Type d'opération hors de la liste RG-T22 (ex. `purchase.create`, recette OFF-09)."""

    code = "OPERATION_NOT_ALLOWED_OFFLINE"


class AvailableInLot2(DomainError):
    """Étape et dépense de voyage (RG-T22) : saisies hors ligne prévues au Lot 2 (camions)."""

    code = "AVAILABLE_IN_LOT_2"


class ProvisionalNumberInvalid(ValidationFailed):
    """Numéro provisoire absent, mal formé, d'un autre type ou d'un autre appareil (RG-T06)."""

    code = "PROVISIONAL_NUMBER_INVALID"


class OperationIdConflict(DomainError):
    """`op_id` déjà utilisé par un autre utilisateur : rien n'est rejoué ni révélé."""

    code = "OP_ID_CONFLICT"
