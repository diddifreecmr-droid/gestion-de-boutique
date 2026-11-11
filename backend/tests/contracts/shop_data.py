"""Données de contrat du socle : une boutique minimale et ses éléments (ports seulement)."""

from collections.abc import Callable
from datetime import UTC, datetime

from app.application.identity.uow import IdentityUnitOfWork
from app.application.ports.uow import UnitOfWork
from app.application.shops.ports import (
    LocationRepository,
    ShopRepository,
    ShopSettingsRepository,
)
from app.application.shops.seeding import default_settings
from app.domain.identity.phone import PhoneNumber
from app.domain.profiles.motos import MOTOS
from app.domain.shared.ids import ShopId
from app.domain.shops.ids import MerchantAccountId
from app.domain.shops.location import Location, LocationDetails
from app.domain.shops.settings import ShopSettings
from app.domain.shops.shop import Shop, ShopIdentity
from app.domain.shops.values import LocationKind, ShopStatus
from tests.contracts.backends import ContractBackend

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)


def shop(shop_id: ShopId, account: MerchantAccountId, name: str = "Motos Garoua") -> Shop:
    return Shop(
        id=shop_id,
        account_id=account,
        profile_code=MOTOS.code,
        identity=ShopIdentity(
            name=name, city="Garoua", phone=PhoneNumber.parse("222000000"), niu="M01"
        ),
        enabled_modules=MOTOS.modules,
        status=ShopStatus.ACTIVE,
        created_at=NOW,
    )


def store(shop_id: ShopId, name: str = "Garoua") -> Location:
    details = LocationDetails(name=name, kind=LocationKind.STORE, is_point_of_sale=True, city="G")
    return Location.seed(shop_id, details)


def commit_platform(
    backend: ContractBackend, action: Callable[[IdentityUnitOfWork], object]
) -> None:
    """Comme `run_in_uow` : l'erreur attendue peut venir de l'écriture **ou** du commit."""
    with backend.platform_uow() as uow:
        action(uow)
        uow.commit()


def seed_shop_and_settings(uow: UnitOfWork, account: MerchantAccountId) -> Location:
    ShopRepository.within(uow).add(shop(uow.shop_id, account))
    location = store(uow.shop_id)
    LocationRepository.within(uow).add(location)
    ShopSettingsRepository.within(uow).add(
        ShopSettings.seed(uow.shop_id, default_settings(MOTOS, location))
    )
    return location
