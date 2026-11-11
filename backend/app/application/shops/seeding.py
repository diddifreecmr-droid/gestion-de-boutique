"""Contenu de départ d'une boutique tiré de son profil (UC-SOC-01 étape 4, recette PLT-01).

Lieux, réglages (reçu, exemplaires, seuil, prix minimum, lieu de réception — Q-01), modes de
paiement (RG-T19), catégories de dépense de base et rattachement du propriétaire, écrits dans
l'unité de travail de la **nouvelle** boutique. Seuls `ShopOpened` et `MemberAdded` sont
journalisés : les éléments de départ découlent du profil, nommé dans l'entrée d'ouverture.
"""

from dataclasses import dataclass
from datetime import datetime

from app.application.ports.uow import UnitOfWork
from app.application.shops.ports import (
    ExpenseCategoryRepository,
    LocationRepository,
    MembershipRepository,
    PaymentModeRepository,
    ShopRepository,
    ShopSettingsRepository,
)
from app.domain.audit.values import Performer
from app.domain.profiles.printing import print_profile_of
from app.domain.profiles.profile import ShopProfile
from app.domain.shared.ids import UserId
from app.domain.shared.roles import Role
from app.domain.shops.expense_category import ExpenseCategory
from app.domain.shops.location import Location, LocationDetails
from app.domain.shops.membership import Membership
from app.domain.shops.payment_mode import PaymentMode, PaymentModeDetails
from app.domain.shops.settings import SettingsValues, ShopSettings
from app.domain.shops.shop import Shop


@dataclass(frozen=True, slots=True, kw_only=True)
class SeedRequest:
    shop: Shop
    profile: ShopProfile
    owner_id: UserId
    performer: Performer
    now: datetime


def default_settings(profile: ShopProfile, reception: Location) -> SettingsValues:
    defaults = profile.settings
    layout = print_profile_of(defaults.receipt_format).layout
    return SettingsValues(
        receipt_format=defaults.receipt_format,
        paper_width_mm=layout.paper_width_mm,
        printable_width_mm=layout.printable_width_mm,
        margin_mm=layout.margin_mm,
        font_size_pt=layout.font_size_pt,
        show_logo=layout.show_logo,
        copies=defaults.copies,
        low_stock_threshold=defaults.low_stock_threshold,
        min_price_enabled=defaults.min_price_enabled,
        exchange_days=defaults.exchange_days,
        truck_silent_hours=defaults.truck_silent_hours,
        transfer_in_transit_days=defaults.transfer_in_transit_days,
        reception_location_id=reception.id,
    )


def seed_shop(uow: UnitOfWork, request: SeedRequest) -> Membership:
    """Écrit la boutique et son contenu de départ ; renvoie le rattachement du propriétaire."""
    shop, profile = request.shop, request.profile
    ShopRepository.within(uow).add(shop)
    locations = LocationRepository.within(uow)
    seeded = [
        Location.seed(
            shop.id,
            LocationDetails(
                name=template.name,
                kind=template.kind,
                is_point_of_sale=template.is_point_of_sale,
                city=template.city,
                display_order=template.display_order,
            ),
        )
        for template in profile.locations
    ]
    for location in seeded:
        locations.add(location)
    reception = next(loc for loc in seeded if loc.name == profile.reception_location)
    ShopSettingsRepository.within(uow).add(
        ShopSettings.seed(shop.id, default_settings(profile, reception))
    )
    modes = PaymentModeRepository.within(uow)
    for order, mode in enumerate(profile.payment_modes, start=1):
        details = PaymentModeDetails(
            name=mode.name, reference_required=mode.reference_required, display_order=order
        )
        modes.add(PaymentMode.seed(shop.id, details))
    categories = ExpenseCategoryRepository.within(uow)
    for order, name in enumerate(profile.expense_categories, start=1):
        categories.add(ExpenseCategory.seed_base(shop.id, name, order))
    owner = Membership.add(
        shop_id=shop.id,
        user_id=request.owner_id,
        role=Role.OWNER,
        location=None,
        profile=profile,
        performer=request.performer,
        now=request.now,
    )
    MembershipRepository.within(uow).add(owner)
    return owner
