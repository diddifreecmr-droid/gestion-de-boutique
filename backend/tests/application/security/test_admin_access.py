"""Administrateur plateforme : accès aux données d'une boutique par délégation seulement."""

from datetime import timedelta

import pytest

from app.application.security.access import Access, AllScope
from app.application.security.actor import Actor, AdminDelegation
from app.application.security.errors import PermissionDenied, ShopAccessDenied
from app.application.security.permissions import READ_PERMISSIONS, Permission
from app.domain.shared.errors import NotFound
from tests.application.security.support import NOW, OTHER_SHOP, SHOP, admin, fixed_policy

policy = fixed_policy()
valid = AdminDelegation.granted_at(SHOP, NOW - timedelta(hours=1))


@pytest.mark.parametrize(
    "actor",
    [
        pytest.param(admin(None), id="sans-delegation"),
        pytest.param(admin(AdminDelegation(SHOP, NOW)), id="expiree-a-l-instant-meme"),
        pytest.param(admin(AdminDelegation(SHOP, NOW - timedelta(seconds=1))), id="expiree"),
        pytest.param(admin(AdminDelegation.granted_at(OTHER_SHOP, NOW)), id="autre-boutique"),
        pytest.param(admin(valid, shop_id=None), id="aucune-boutique-visee"),
    ],
)
def test_admin_without_active_delegation_is_treated_as_non_member(actor: Actor) -> None:
    with pytest.raises(NotFound) as caught:
        policy.require(actor, Permission.SALE_READ)
    error = caught.value
    assert isinstance(error, ShopAccessDenied)
    assert error.code == "NOT_FOUND"
    assert dict(error.details) == {}  # aucune fuite d'existence (specs § 8.3)
    assert error.actor is actor
    assert error.permission is Permission.SALE_READ
    assert policy.can_read_field(actor, Permission.COST_READ) is False


@pytest.mark.parametrize("permission", sorted(READ_PERMISSIONS))
def test_valid_delegation_grants_read_on_read_permissions(permission: Permission) -> None:
    actor = admin(valid)
    assert policy.require(actor, permission) is Access.READ
    assert policy.scope_filter(actor, permission) == AllScope()


@pytest.mark.parametrize("permission", sorted(set(Permission) - READ_PERMISSIONS))
def test_valid_delegation_never_grants_a_write(permission: Permission) -> None:
    with pytest.raises(PermissionDenied) as caught:
        policy.require(admin(valid), permission)
    assert dict(caught.value.details) == {
        "permission": permission.value,
        "role": "platform_admin",
    }


def test_valid_delegation_lets_presenters_show_fields() -> None:
    assert policy.can_read_field(admin(valid), Permission.COST_READ) is True


def test_delegation_expires_with_the_injected_clock() -> None:
    actor = admin(valid)
    later = fixed_policy(valid.expires_at)
    with pytest.raises(ShopAccessDenied):
        later.require(actor, Permission.SALE_READ)
    just_before = fixed_policy(valid.expires_at - timedelta(microseconds=1))
    assert just_before.require(actor, Permission.SALE_READ) is Access.READ


def test_naive_clock_is_rejected() -> None:
    naive = fixed_policy(NOW.replace(tzinfo=None))
    with pytest.raises(ValueError, match="UTC"):
        naive.require(admin(valid), Permission.SALE_READ)
