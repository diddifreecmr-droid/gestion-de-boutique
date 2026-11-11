"""Policy pour les membres : refus explicite, portées OWN/ALL, champs (RG-D01 à RG-D05)."""

import pytest

from app.application.security.access import Access, AllScope, OwnScope
from app.application.security.errors import PermissionDenied, PlatformAdminRequired
from app.application.security.permissions import FIELD_PERMISSIONS, Mode, Permission
from app.application.security.roles import Role
from app.domain.shared.errors import Forbidden
from app.domain.shared.ids import UserId
from tests.application.security.support import admin, fixed_policy, member

policy = fixed_policy()


def test_refusal_is_a_forbidden_with_stable_code_and_details() -> None:
    seller = member(Role.SELLER)
    with pytest.raises(Forbidden) as caught:
        policy.require(seller, Permission.COST_READ)
    error = caught.value
    assert isinstance(error, PermissionDenied)
    assert error.code == "FORBIDDEN"
    assert error.message == "Accès refusé"
    assert dict(error.details) == {"permission": "COST_READ", "role": "seller"}
    # Informations exposées pour l'entrée « Accès refusé » du journal (T09).
    assert error.actor is seller
    assert error.permission is Permission.COST_READ


def test_require_returns_the_granted_access() -> None:
    assert policy.require(member(Role.OWNER), Permission.SALE_READ) is Access.ALL
    assert policy.require(member(Role.SELLER), Permission.SALE_READ) is Access.OWN
    assert policy.require(member(Role.ACCOUNTANT), Permission.LOCATION_READ) is Access.READ


def test_own_scope_filters_on_the_actor_user() -> None:
    user_id = UserId.new()
    seller = member(Role.SELLER, user_id)
    assert policy.scope_filter(seller, Permission.SALE_READ) == OwnScope(user_id)
    assert policy.scope_filter(seller, Permission.RECEIVABLE_READ) == OwnScope(user_id)
    driver = member(Role.DRIVER, user_id)
    assert policy.scope_filter(driver, Permission.TRIP_READ) == OwnScope(user_id)


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        (Role.OWNER, Permission.SALE_READ),
        (Role.ACCOUNTANT, Permission.LOCATION_READ),  # « Lecture » : tout, sans modifier
        (Role.ACCOUNTANT, Permission.EXPENSE_READ),
    ],
)
def test_all_scope_for_all_and_read(role: Role, permission: Permission) -> None:
    assert policy.scope_filter(member(role), permission) == AllScope()


def test_scope_filter_refuses_instead_of_returning_an_empty_scope() -> None:
    with pytest.raises(PermissionDenied):
        policy.scope_filter(member(Role.ACCOUNTANT), Permission.SALE_READ)


@pytest.mark.parametrize(
    ("role", "field", "readable"),
    [
        (Role.SELLER, Permission.COST_READ, False),  # RG-D02
        (Role.ACCOUNTANT, Permission.SALES_DATA_READ, False),  # RG-D03
        (Role.DRIVER, Permission.PRICE_READ, False),  # RG-D05
        (Role.DRIVER, Permission.COST_READ, False),
        (Role.DRIVER, Permission.SELLING_PRICE_READ, False),
        (Role.ACCOUNTANT, Permission.SELLING_PRICE_READ, False),  # Q-14
        (Role.SELLER, Permission.AUDIT_READ, False),
        (Role.OWNER, Permission.COST_READ, True),
        (Role.ACCOUNTANT, Permission.COST_READ, True),
        (Role.SELLER, Permission.SALES_DATA_READ, True),  # ses ventes (portée OWN)
        (Role.SELLER, Permission.PRICE_READ, True),
    ],
)
def test_can_read_field(role: Role, field: Permission, readable: bool) -> None:
    assert policy.can_read_field(member(role), field) is readable


def test_can_read_field_rejects_a_non_field_permission() -> None:
    with pytest.raises(ValueError, match="permission de champ"):
        policy.can_read_field(member(Role.OWNER), Permission.SALE_CREATE)


def test_field_permissions_are_read_permissions() -> None:
    assert all(permission.mode is Mode.READ for permission in FIELD_PERMISSIONS)


def test_platform_console_is_for_the_admin_only() -> None:
    policy.require_platform_admin(admin(shop_id=None))
    owner = member(Role.OWNER)
    with pytest.raises(PlatformAdminRequired) as caught:
        policy.require_platform_admin(owner)
    assert caught.value.code == "FORBIDDEN"
    assert dict(caught.value.details) == {"permission": "PLATFORM_ADMIN", "role": "owner"}
    assert caught.value.actor is owner


def test_member_without_role_is_refused_even_if_invariant_bypassed() -> None:
    actor = member(Role.OWNER)
    object.__setattr__(actor, "role", None)  # contourne volontairement le dataclass figé
    with pytest.raises(RuntimeError, match="sans rôle"):
        policy.require(actor, Permission.SALE_READ)
