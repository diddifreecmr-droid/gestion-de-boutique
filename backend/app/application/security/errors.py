"""Refus d'accès levés par la `Policy`, prêts à être journalisés (RG-D01, TR-04).

Les codes restent ceux du catalogue (specs § 6.2) : `FORBIDDEN` (403) et `NOT_FOUND` (404). Les
exceptions portent en plus l'acteur et la permission pour que le journal (T09) inscrive
« Accès refusé » sans rien recalculer ; ces attributs ne sont pas sérialisés vers le client.
"""

from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.domain.shared.errors import DomainError, Forbidden, NotFound

PLATFORM_ADMIN_LABEL = "platform_admin"
"""Valeur de `details.role` quand l'acteur est l'administrateur plateforme."""


def role_label(actor: Actor) -> str:
    if actor.role is not None:
        return actor.role.value
    return PLATFORM_ADMIN_LABEL


class PermissionDenied(Forbidden):
    """Permission absente ou insuffisante (« Lecture » sur une écriture) → 403 `FORBIDDEN`."""

    def __init__(self, actor: Actor, permission: Permission) -> None:
        super().__init__(
            "Accès refusé",
            details={"permission": permission.value, "role": role_label(actor)},
        )
        self.actor = actor
        self.permission = permission


class ShopAccessDenied(NotFound):
    """Admin sans délégation active pour la boutique visée → 404, comme un non-membre (§ 8.3).

    Le 404 évite de révéler l'existence de la boutique ; `details` reste vide.
    """

    def __init__(self, actor: Actor, permission: Permission) -> None:
        super().__init__("Boutique introuvable")
        self.actor = actor
        self.permission = permission


class PlatformAdminRequired(Forbidden):
    """Opération de la console plateforme demandée par un membre de boutique → 403."""

    def __init__(self, actor: Actor) -> None:
        super().__init__(
            "Accès refusé",
            details={"permission": "PLATFORM_ADMIN", "role": role_label(actor)},
        )
        self.actor = actor


class RateLimited(DomainError):
    """Trop de demandes sur `/auth/*` (specs § 8.1) → 429 avec `Retry-After` (code ajouté T10).

    Contrat (T10b) : corps `{"error": {"code": "RATE_LIMITED", "message", "details":
    {"retry_after": <secondes>}}}` — `retry_after` est un **entier de secondes ≥ 1** (arrondi
    au supérieur), et la même valeur part dans l'en-tête `Retry-After` (RFC 9110 § 10.2.3,
    forme « delay-seconds »). Le client attend ce délai avant de réessayer.
    """

    code = "RATE_LIMITED"

    def __init__(self, retry_after_seconds: int) -> None:
        if retry_after_seconds < 1:
            msg = "Un délai d'attente est d'au moins une seconde"
            raise ValueError(msg)
        super().__init__(
            "Trop de tentatives : réessayez plus tard",
            details={"retry_after": retry_after_seconds},
        )
        self.retry_after = retry_after_seconds
