"""Sécurité applicative : Actor, Permission, Policy (tâche T07, specs § 8.2 à 8.3)."""

from app.application.security.access import Access, AllScope, OwnScope, Scope
from app.application.security.actor import Actor, AdminDelegation
from app.application.security.errors import (
    PermissionDenied,
    PlatformAdminRequired,
    ShopAccessDenied,
)
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.security.roles import Role

__all__ = [
    "Access",
    "Actor",
    "AdminDelegation",
    "AllScope",
    "OwnScope",
    "Permission",
    "PermissionDenied",
    "PlatformAdminRequired",
    "Policy",
    "Role",
    "Scope",
    "ShopAccessDenied",
]
