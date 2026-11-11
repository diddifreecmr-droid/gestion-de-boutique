"""Assemblage du socle des boutiques (T10) : console plateforme, profil, réglages, lieux,
modes de paiement, membres, délégation de l'administrateur.

`LocationStock` : `LedgerLocationStock` du module Stock (T14), sur la projection `stock_level`.
"""

from dataclasses import dataclass

from app.application.identity.ports import TemporaryPinGenerator
from app.application.identity.use_cases.member_access import MemberAccess
from app.application.identity.use_cases.reset_pin import ResetPin
from app.application.identity.use_cases.revoke_user_devices import RevokeUserDevices
from app.application.identity.use_cases.unlock_user import UnlockUser
from app.application.security.policy import Policy
from app.application.shops.stock_probe import LocationStock
from app.application.shops.use_cases.admin_access import GrantAdminAccess, RevokeAdminAccess
from app.application.shops.use_cases.get_shop_profile import GetShopProfile
from app.application.shops.use_cases.manage_locations import ManageLocations
from app.application.shops.use_cases.manage_members import ManageMembers
from app.application.shops.use_cases.manage_payment_modes import ManagePaymentModes
from app.application.shops.use_cases.open_shop import OpenShop
from app.application.shops.use_cases.platform_shops import PlatformShops
from app.application.shops.use_cases.shop_settings import ShopSettingsUseCase
from app.application.stock.probes import LedgerLocationStock
from app.bootstrap.identity import IdentityModule
from app.bootstrap.journal import shop_entitlements
from app.infrastructure.auth.opaque_tokens import RandomPinGenerator
from app.interface.http.routes.shop_components import ShopsComponents


@dataclass(frozen=True, slots=True, kw_only=True)
class ShopsModule:
    http: ShopsComponents


def build_shops(
    identity: IdentityModule,
    *,
    pins: TemporaryPinGenerator | None = None,
    stock: LocationStock | None = None,
) -> ShopsModule:
    core, clock, hasher = identity.core, identity.clock, identity.hasher
    pins = pins or RandomPinGenerator()
    shop_uows, platform_uows = core.shop_uow_factory, core.platform_uow_factory
    policy = Policy(clock=clock.now)
    access = MemberAccess(policy, core.memberships)
    http = ShopsComponents(
        open_shop=OpenShop(platform_uows, policy, hasher, pins, clock),
        platform=PlatformShops(shop_uows, core.catalog, core.overrides, policy, clock),
        profile=GetShopProfile(shop_uows, policy, shop_entitlements(core)),
        settings=ShopSettingsUseCase(shop_uows, policy, clock),
        locations=ManageLocations(shop_uows, policy, stock or LedgerLocationStock(), clock),
        payment_modes=ManagePaymentModes(shop_uows, policy, clock),
        members=ManageMembers(platform_uows, policy, hasher, pins, clock),
        reset_pin=ResetPin(platform_uows, access, hasher, pins, clock),
        revoke_devices=RevokeUserDevices(platform_uows, access, clock),
        unlock=UnlockUser(platform_uows, access, clock),
        grant_admin=GrantAdminAccess(shop_uows, policy, clock),
        revoke_admin=RevokeAdminAccess(shop_uows, policy, clock),
        guard=identity.auth.guard,
    )
    return ShopsModule(http=http)
