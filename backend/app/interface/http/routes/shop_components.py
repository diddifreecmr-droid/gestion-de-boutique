"""Cas d'utilisation du socle des boutiques, assemblés par la composition root (T10)."""

from dataclasses import dataclass

from app.application.identity.use_cases.reset_pin import ResetPin
from app.application.identity.use_cases.revoke_user_devices import RevokeUserDevices
from app.application.identity.use_cases.unlock_user import UnlockUser
from app.application.shops.use_cases.admin_access import GrantAdminAccess, RevokeAdminAccess
from app.application.shops.use_cases.get_shop_profile import GetShopProfile
from app.application.shops.use_cases.manage_locations import ManageLocations
from app.application.shops.use_cases.manage_members import ManageMembers
from app.application.shops.use_cases.manage_payment_modes import ManagePaymentModes
from app.application.shops.use_cases.open_shop import OpenShop
from app.application.shops.use_cases.platform_access import PlatformShopAccess
from app.application.shops.use_cases.platform_shops import PlatformShops
from app.application.shops.use_cases.shop_settings import ShopSettingsUseCase
from app.interface.http.security import AuthGuard


@dataclass(frozen=True, slots=True, kw_only=True)
class ShopsComponents:
    open_shop: OpenShop
    platform: PlatformShops
    profile: GetShopProfile
    settings: ShopSettingsUseCase
    locations: ManageLocations
    payment_modes: ManagePaymentModes
    members: ManageMembers
    reset_pin: ResetPin
    revoke_devices: RevokeUserDevices
    unlock: UnlockUser
    grant_admin: GrantAdminAccess
    revoke_admin: RevokeAdminAccess
    platform_access: PlatformShopAccess
    guard: AuthGuard
