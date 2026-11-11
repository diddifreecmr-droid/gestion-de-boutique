"""Politique d'autorisation : seul point de décision des droits (specs § 8.2, TR-04, RG-D01).

- `require` renvoie l'accès accordé ou **lève** une erreur ; jamais de booléen silencieux.
- `scope_filter` traduit « Siens » en filtre de requête pour le dépôt (`OwnScope`).
- `can_read_field` répond aux présentateurs (TR-05) pour les permissions de champ.

Administrateur plateforme : sans délégation active pour la boutique visée, il est traité comme
un non-membre (`ShopAccessDenied`, 404). Avec délégation, il **consulte** seulement : `READ` sur
les permissions de lecture, refus sur toute écriture (CDC § 4.1 « assiste », « ne consulte pas
les données sans l'accord du propriétaire »).
"""

from collections.abc import Callable
from datetime import datetime

from app.application.security.access import Access, AllScope, OwnScope, Scope
from app.application.security.actor import Actor, require_utc
from app.application.security.errors import (
    PermissionDenied,
    PlatformAdminRequired,
    ShopAccessDenied,
)
from app.application.security.permissions import FIELD_PERMISSIONS, Mode, Permission
from app.application.security.role_matrix import access_for

type UtcClock = Callable[[], datetime]


class Policy:
    """Décide à partir de la matrice `ROLE_MATRIX` ; l'horloge (UTC aware) est injectée."""

    def __init__(self, clock: UtcClock) -> None:
        self._clock = clock

    def require(self, actor: Actor, permission: Permission) -> Access:
        """Accès accordé (`OWN`, `READ` ou `ALL`) ; lève `PermissionDenied` sinon."""
        access = self._access(actor, permission)
        if access is Access.NONE:
            raise PermissionDenied(actor, permission)
        return access

    def scope_filter(self, actor: Actor, permission: Permission) -> Scope:
        """Portée à appliquer dans la requête du dépôt ; lève si la permission est absente."""
        if self.require(actor, permission) is Access.OWN:
            return OwnScope(actor.user_id)
        return AllScope()

    def can_read_field(self, actor: Actor, field_permission: Permission) -> bool:
        """Le présentateur peut-il inclure ce champ ? Seules les permissions de champ."""
        if field_permission not in FIELD_PERMISSIONS:
            msg = f"{field_permission} n'est pas une permission de champ"
            raise ValueError(msg)
        if actor.is_platform_admin and not self._delegation_active(actor):
            return False
        return self._access(actor, field_permission) is not Access.NONE

    def require_platform_admin(self, actor: Actor) -> None:
        """Console plateforme (UC-SOC-01) : réservée à l'administrateur."""
        if not actor.is_platform_admin:
            raise PlatformAdminRequired(actor)

    # ------------------------------------------------------------------ interne
    def _access(self, actor: Actor, permission: Permission) -> Access:
        if not actor.is_platform_admin:
            if actor.role is None:  # exclu par Actor.__post_init__ : défense en profondeur
                msg = "Membre de boutique sans rôle"
                raise RuntimeError(msg)
            return access_for(actor.role, permission)
        if not self._delegation_active(actor):
            raise ShopAccessDenied(actor, permission)
        return Access.READ if permission.mode is Mode.READ else Access.NONE

    def _delegation_active(self, actor: Actor) -> bool:
        if actor.delegation is None or actor.shop_id is None:
            return False
        now = require_utc(self._clock(), "Policy.clock()")
        return actor.delegation.allows(actor.shop_id, now)
