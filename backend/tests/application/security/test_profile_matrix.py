"""Cellules de la matrice qui dépendent du type de boutique (décision client du 2026-11-15).

« Seul le gérant voit le stock » en Prêt-à-porter et Textile : le vendeur perd `STOCK_READ`
(routes de stock) mais garde `ARTICLE_READ` (liste des articles de la vente, avec pastille).
Motos et un acteur sans profil (matrice du CDC) : inchangés. Toutes les autres cellules sont
identiques d'un profil à l'autre.
"""

import pytest

from app.application.security.access import Access
from app.application.security.actor import Actor
from app.application.security.errors import PermissionDenied
from app.application.security.permissions import Permission
from app.application.security.role_matrix import ROLE_MATRIX
from app.application.security.roles import Role
from app.domain.profiles.profile import ProfileCode
from app.domain.shared.ids import DeviceId, UserId
from tests.application.security.support import SHOP, fixed_policy

RESERVED = (ProfileCode.APPAREL, ProfileCode.TEXTILE)
STOCK_ROLES = {Role.OWNER: Access.ALL, Role.SELLER: Access.READ, Role.ACCOUNTANT: Access.ALL}


def _actor(role: Role, profile: ProfileCode | None) -> Actor:
    return Actor.member(
        user_id=UserId.new(), device_id=DeviceId.new(), shop_id=SHOP, role=role, profile=profile
    )


def _expected(profile: ProfileCode | None, role: Role, permission: Permission) -> Access:
    if profile in RESERVED and role is Role.SELLER and permission is Permission.STOCK_READ:
        return Access.NONE
    return ROLE_MATRIX[permission][role]


@pytest.mark.parametrize("profile", [None, *ProfileCode], ids=lambda p: str(p))
@pytest.mark.parametrize("role", list(Role), ids=lambda r: r.value)
@pytest.mark.parametrize("permission", list(Permission), ids=lambda p: p.value)
def test_cell_by_profile(profile: ProfileCode | None, role: Role, permission: Permission) -> None:
    policy, actor = fixed_policy(), _actor(role, profile)
    expected = _expected(profile, role, permission)
    if expected is Access.NONE:
        with pytest.raises(PermissionDenied):
            policy.require(actor, permission)
    else:
        assert policy.require(actor, permission) is expected


@pytest.mark.parametrize("profile", [None, *ProfileCode], ids=lambda p: str(p))
@pytest.mark.parametrize(("role", "access"), STOCK_ROLES.items(), ids=lambda v: str(v))
def test_stock_reserved_to_owner(profile: ProfileCode | None, role: Role, access: Access) -> None:
    policy, actor = fixed_policy(), _actor(role, profile)
    reserved = profile in RESERVED and role is Role.SELLER
    assert policy.allows(actor, Permission.STOCK_READ) is not reserved
    assert policy.require(actor, Permission.ARTICLE_READ) is access  # la vente liste toujours


def test_actor_profile_is_typed() -> None:
    with pytest.raises(TypeError):
        _actor(Role.SELLER, "textile")  # type: ignore[arg-type]  # refus prouvé
