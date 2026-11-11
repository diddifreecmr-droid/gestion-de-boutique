"""Rattachements de test écrits par les **vrais** dépôts (boutique minimale, lieu de vente).

Remplace l'ancien `InMemoryMembershipDirectory.grant` pour les tests qui passent par la
composition root : `MembershipDirectory` lit désormais l'agrégat `Membership`.
"""

from datetime import UTC, datetime

from app.application.ports.uow import UnitOfWorkFactory
from app.application.shops.ports import LocationRepository, MembershipRepository, ShopRepository
from app.domain.identity.phone import PhoneNumber
from app.domain.profiles.motos import MOTOS
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.roles import Role
from app.domain.shops.ids import MembershipId, MerchantAccountId
from app.domain.shops.location import Location, LocationDetails
from app.domain.shops.membership import Membership
from app.domain.shops.shop import Shop, ShopIdentity
from app.domain.shops.values import LocationKind, ShopStatus

CREATED = datetime(2026, 11, 1, 8, 0, tzinfo=UTC)


def grant(
    uow_factory: UnitOfWorkFactory,
    user_id: UserId,
    shop_id: ShopId,
    role: Role,
    shop_name: str = "Motos Garoua",
) -> Membership:
    """Rattache `user_id` à `shop_id` (créée au besoin, profil Motos) ; vendeur → Garoua."""
    with uow_factory(shop_id) as uow:
        shops = ShopRepository.within(uow)
        if shops.find(shop_id) is None:
            shops.add(
                Shop(
                    id=shop_id,
                    account_id=MerchantAccountId.new(),
                    profile_code=MOTOS.code,
                    identity=ShopIdentity(
                        name=shop_name, city="Garoua", phone=PhoneNumber.parse("699000000")
                    ),
                    enabled_modules=MOTOS.modules,
                    status=ShopStatus.ACTIVE,
                    created_at=CREATED,
                )
            )
        location = None
        if role is Role.SELLER:
            location = Location.seed(
                shop_id,
                LocationDetails(
                    name=f"Garoua {user_id}", kind=LocationKind.STORE, is_point_of_sale=True
                ),
            )
            LocationRepository.within(uow).add(location)
        membership = Membership(
            id=MembershipId.new(),
            shop_id=shop_id,
            user_id=user_id,
            role=role,
            default_location_id=None if location is None else location.id,
        )
        MembershipRepository.within(uow).add(membership)
        uow.commit()
    return membership
