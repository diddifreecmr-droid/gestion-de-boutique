"""Combinaisons de modules d'une boutique (décision client specs § 15.1, 2026-11-12)."""

from datetime import UTC, datetime

import pytest

from app.domain.audit.values import Performer
from app.domain.identity.phone import PhoneNumber
from app.domain.profiles.apparel import APPAREL
from app.domain.profiles.modules import (
    ALL_MODULES,
    MANDATORY_MODULES,
    OPTIONAL_MODULES,
    Module,
    broken_dependencies,
    missing_mandatory,
)
from app.domain.profiles.motos import MOTOS
from app.domain.profiles.profile import ShopProfile
from app.domain.shared.errors import Forbidden
from app.domain.shared.ids import ShopId, UserId
from app.domain.shops.errors import (
    ModuleDependency,
    ModuleDisabled,
    ModuleMandatory,
    ModuleNotAvailable,
)
from app.domain.shops.ids import MerchantAccountId
from app.domain.shops.modules import checked_modules
from app.domain.shops.shop import Shop, ShopIdentity

NOW = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
WHO = Performer(UserId.new(), "admin")
MINIMAL = MANDATORY_MODULES


def _shop(profile: ShopProfile = MOTOS, modules: frozenset[Module] = MOTOS.modules) -> Shop:
    identity = ShopIdentity(name="Motos", city="Garoua", phone=PhoneNumber.parse("222000000"))
    return Shop.open(
        shop_id=ShopId.new(), account_id=MerchantAccountId.new(), profile_code=profile.code,
        identity=identity, modules=modules, performer=WHO, now=NOW,
    )  # fmt: skip


def _administer(shop: Shop, modules: frozenset[Module] | list[Module]) -> bool:
    profile = MOTOS if shop.profile_code == MOTOS.code else APPAREL
    return shop.administer(
        modules=modules, status=None, available=profile.available_modules,
        performer=WHO, now=NOW,
    )  # fmt: skip


def test_mandatory_and_optional_modules_follow_the_client_decision() -> None:
    assert {Module.CORE, Module.AUDIT, Module.CATALOG, Module.SALES} == MANDATORY_MODULES
    assert OPTIONAL_MODULES == ALL_MODULES - MANDATORY_MODULES
    assert missing_mandatory([Module.CORE]) == [Module.AUDIT, Module.CATALOG, Module.SALES]
    assert broken_dependencies([*MINIMAL, Module.TRANSPORT]) == [
        (Module.TRANSPORT, Module.TRANSFERS)
    ]
    assert broken_dependencies([*MINIMAL, Module.TRANSPORT, Module.TRANSFERS]) == []


def test_profile_defaults_are_unchanged() -> None:
    assert MOTOS.modules == ALL_MODULES
    assert APPAREL.modules == ALL_MODULES - {Module.TRANSPORT, Module.TRANSFERS}
    assert broken_dependencies(MOTOS.modules) == broken_dependencies(APPAREL.modules) == []


def test_minimal_shop_and_every_valid_combination_is_accepted() -> None:
    shop = _shop(modules=MINIMAL)
    assert shop.enabled_modules == MINIMAL
    assert _administer(shop, [*MINIMAL, Module.TRANSFERS, Module.TRANSPORT])
    assert not _administer(shop, [*MINIMAL, Module.TRANSPORT, Module.TRANSFERS])  # inchangé
    assert _administer(shop, MINIMAL)
    assert shop.enabled_modules == MINIMAL


@pytest.mark.parametrize("mandatory", sorted(MANDATORY_MODULES))
def test_a_mandatory_module_is_never_disabled(mandatory: Module) -> None:
    shop = _shop()
    with pytest.raises(ModuleMandatory) as refused:
        _administer(shop, ALL_MODULES - {mandatory})
    assert refused.value.details == {"module": mandatory.value}
    assert shop.enabled_modules == ALL_MODULES  # rien n'a bougé
    with pytest.raises(ModuleMandatory):
        _shop(modules=MINIMAL - {mandatory})


def test_transport_requires_transfers_at_opening_and_at_patch() -> None:
    with pytest.raises(ModuleDependency) as refused:
        _shop(modules=ALL_MODULES - {Module.TRANSFERS})
    assert refused.value.code == "MODULE_DEPENDENCY"
    assert refused.value.details == {"module": "transport", "requires": "transfers"}
    shop = _shop()
    with pytest.raises(ModuleDependency):
        _administer(shop, ALL_MODULES - {Module.TRANSFERS})
    assert shop.enabled_modules == ALL_MODULES


def test_a_module_outside_the_profile_is_refused_first() -> None:
    with pytest.raises(ModuleNotAvailable):
        checked_modules(
            [Module.TRANSPORT], profile=APPAREL.code, available=APPAREL.available_modules
        )
    with pytest.raises(ModuleNotAvailable):
        _administer(_shop(APPAREL, APPAREL.modules), [*MINIMAL, Module.TRANSPORT])


def test_require_module_raises_a_typed_403() -> None:
    shop = _shop(modules=MINIMAL)
    shop.require_module(Module.SALES)
    assert not shop.has_module(Module.RECEIVABLES)
    with pytest.raises(ModuleDisabled) as refused:
        shop.require_module(Module.RECEIVABLES)
    assert isinstance(refused.value, Forbidden)
    assert refused.value.code == "MODULE_DISABLED"
    assert refused.value.details == {"module": "receivables"}
