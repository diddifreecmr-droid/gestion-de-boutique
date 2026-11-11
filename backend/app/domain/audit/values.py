"""Valeurs du journal : action, élément visé, changement de champ, auteur (CDC § 16.1).

Les valeurs avant/après d'un changement sont des **scalaires JSON** (`str`, `int`, `bool`,
`None`) : un montant s'inscrit en FCFA entiers, une quantité en chaîne décimale (« 2.5 »), une
date en ISO 8601. Un `float` est refusé (aucun arrondi caché dans une trace légale).
"""

import re
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.domain.shared.ids import DeviceId, UserId

TEXT_MAX = 500
_CODE = re.compile(r"^[a-z][a-z0-9_]*$")

type Scalar = str | int | bool | None


class AuditAction(StrEnum):
    """Les onze actions du CDC § 16.1 (code stable ; libellé français dans `label`)."""

    CREATE = "create"
    UPDATE = "update"
    CANCEL = "cancel"
    VALIDATE = "validate"
    REJECT = "reject"
    LOGIN = "login"
    LOGOUT = "logout"
    PRINT = "print"
    IMPORT = "import"
    CONFIGURE = "configure"
    """« Régler » : changement de réglage de la boutique (RG-T01, filtre « réglage »)."""
    ACCESS_DENIED = "access_denied"

    @property
    def label(self) -> str:
        return _LABELS[self]


_LABELS = {
    AuditAction.CREATE: "Créer",
    AuditAction.UPDATE: "Modifier",
    AuditAction.CANCEL: "Annuler",
    AuditAction.VALIDATE: "Valider",
    AuditAction.REJECT: "Rejeter",
    AuditAction.LOGIN: "Se connecter",
    AuditAction.LOGOUT: "Se déconnecter",
    AuditAction.PRINT: "Imprimer",
    AuditAction.IMPORT: "Importer",
    AuditAction.CONFIGURE: "Régler",
    AuditAction.ACCESS_DENIED: "Accès refusé",
}

SENSITIVE_ACTIONS = frozenset({AuditAction.CANCEL})
"""Actions toujours signalées par une pastille (UC-JRN-01) ; les autres le sont par l'événement."""


def require_code(value: object, name: str) -> str:
    """Code technique en `snake_case` (type d'élément, module, rôle)."""
    if not isinstance(value, str) or not _CODE.fullmatch(value) or len(value) > 64:
        msg = f"{name} doit être un code snake_case (≤ 64), reçu {value!r}"
        raise ValueError(msg)
    return value


def require_text(value: object, name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > TEXT_MAX:
        msg = f"{name} : texte non vide de {TEXT_MAX} caractères au plus attendu"
        raise ValueError(msg)
    return value


def require_scalar(value: object, name: str) -> Scalar:
    if value is None or isinstance(value, str | bool | int):
        return value
    msg = f"{name} : scalaire JSON attendu (str, int, bool, None), reçu {type(value).__name__}"
    raise TypeError(msg)


@dataclass(frozen=True, slots=True)
class EntityRef:
    """Élément visé : type (`sale`, `user`…), identifiant et numéro lisible (`V-000124`)."""

    type: str
    id: UUID | None = None
    number: str | None = None

    def __post_init__(self) -> None:
        require_code(self.type, "EntityRef.type")
        if self.id is not None and not isinstance(self.id, UUID):
            msg = "EntityRef.id doit être un UUID"
            raise TypeError(msg)
        require_text(self.number, "EntityRef.number", optional=True)


@dataclass(frozen=True, slots=True)
class FieldChange:
    """Valeur avant et après d'un champ modifié (UC-JRN-02)."""

    field: str
    before: Scalar
    after: Scalar

    def __post_init__(self) -> None:
        require_code(self.field, "FieldChange.field")
        require_scalar(self.before, "FieldChange.before")
        require_scalar(self.after, "FieldChange.after")


@dataclass(frozen=True, slots=True)
class Performer:
    """Qui a agi : utilisateur, rôle **au moment de l'action**, appareil (RG-T04).

    `role` est le code stable du rôle (`owner`, `seller`… ou `platform_admin`) : le domaine ne
    dépend pas de l'énumération de la couche application. `device_id` est absent pour une
    action du serveur lui-même (tâche planifiée).
    """

    user_id: UserId
    role: str
    device_id: DeviceId | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, UserId):
            msg = "Performer.user_id doit être un UserId"
            raise TypeError(msg)
        require_code(self.role, "Performer.role")
        if self.device_id is not None and not isinstance(self.device_id, DeviceId):
            msg = "Performer.device_id doit être un DeviceId"
            raise TypeError(msg)
