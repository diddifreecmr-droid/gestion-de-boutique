"""UC-SOC-01 — `OpenShop` (recette PLT-01, PLT-02, PLT-04 côté application)."""

from decimal import Decimal

import pytest

from app.application.audit.ports import AuditQuery
from app.application.security.errors import PlatformAdminRequired
from app.application.shops.ports import (
    ExpenseCategoryRepository,
    LocationRepository,
    PaymentModeRepository,
    ShopSettingsRepository,
)
from app.application.shops.use_cases.open_shop import OpenShopCommand
from app.domain.profiles.printing import ReceiptFormat
from app.domain.shared.errors import Duplicate, ValidationFailed
from app.domain.shared.roles import Role
from app.domain.shops.errors import UnknownProfile
from app.domain.shops.values import LocationKind
from tests.application.shops.support import ADMIN_PHONE, OWNER_PHONE, World, motos_command


def test_motos_shop_gets_the_profile_defaults() -> None:
    world = World()
    opened = world.open_motos()
    assert opened.owner_created
    assert opened.temporary_pin == "482915"
    with world.core.shop_uow_factory(opened.shop_id) as uow:
        locations = LocationRepository.within(uow).list_all()
        settings = ShopSettingsRepository.within(uow).current().values
        modes = PaymentModeRepository.within(uow).list_all()
        categories = ExpenseCategoryRepository.within(uow).list_all()
    assert [(loc.name, loc.details.kind, loc.details.is_point_of_sale) for loc in locations] == [
        ("Garoua-Boulaï", LocationKind.WAREHOUSE, False),
        ("Ngaoundéré", LocationKind.WAREHOUSE, False),
        ("Garoua", LocationKind.STORE, True),
    ]
    assert settings.receipt_format is ReceiptFormat.MM80
    assert (settings.copies, settings.low_stock_threshold) == (1, Decimal(2))
    assert settings.min_price_enabled is False
    assert settings.reception_location_id == locations[2].id  # Q-01 : Garoua au Lot 1
    assert [m.name for m in modes][:3] == ["Espèces", "Orange Money", "MTN Mobile Money"]
    assert len(modes) == 6
    assert [c.name for c in categories] == ["Carburant", "Repas", "Salaire", "Loyer", "Autre"]
    owner = world.user(OWNER_PHONE)
    assert owner.must_change_pin
    view = world.identity.memberships.find(owner.id, opened.shop_id)
    assert view is not None
    assert view.role is Role.OWNER
    assert view.usable
    actions = [e.action.value for e in world.journal(opened.shop_id)]
    assert sorted(actions) == ["create", "create"]  # boutique ouverte, propriétaire ajouté


def test_known_phone_is_attached_without_duplicate_or_new_code() -> None:
    world = World()
    first = world.open_motos()
    second = world.open_motos(name="Motos Ngaoundéré")
    assert (second.owner_id, second.owner_created, second.temporary_pin) == (
        first.owner_id,
        False,
        None,
    )
    assert second.account_id == first.account_id  # même compte commerçant (même téléphone)
    shops = [view.shop_name for view in world.identity.memberships.for_user(first.owner_id)]
    assert shops == ["Motos Garoua", "Motos Ngaoundéré"]


def test_shop_name_is_unique_in_the_account_and_nothing_is_written() -> None:
    world = World()
    world.open_motos()
    with pytest.raises(Duplicate) as caught:
        world.open_motos(name="  motos   GAROUA ")
    assert caught.value.details["constraint"] == "shop_name_in_account"
    assert len(world.core.catalog.list_all()) == 1


def test_only_the_platform_admin_opens_a_shop() -> None:
    world = World()
    opened = world.open_motos()
    with pytest.raises(PlatformAdminRequired):
        world.http.open_shop.execute(world.owner(opened), motos_command("Autre"))


def test_invalid_inputs_are_refused_before_any_write() -> None:
    world = World()
    with pytest.raises(UnknownProfile):
        world.http.open_shop.execute(
            world.admin, OpenShopCommand(**{**_base(), "profile_code": "x"})
        )
    with pytest.raises(ValidationFailed) as caught:
        world.http.open_shop.execute(world.admin, OpenShopCommand(**{**_base(), "phone": "12"}))
    assert caught.value.details["field"] == "phone"
    with pytest.raises(ValidationFailed) as owner:
        world.http.open_shop.execute(world.admin, motos_command(owner_phone=ADMIN_PHONE))
    assert owner.value.details["field"] == "owner_phone"
    assert world.core.catalog.list_all() == []


def test_a_failure_in_the_shop_part_leaves_no_account_and_no_user() -> None:
    """Transaction commune : le propriétaire créé n'est pas validé sans sa boutique."""
    world = World()
    world.pins.codes = iter([])  # le tirage du code échoue après le compte, avant la boutique
    with pytest.raises(StopIteration):
        world.open_motos()
    with world.core.platform_uow_factory() as uow:
        assert uow.users.find_by_phone(world.user(ADMIN_PHONE).phone) is not None
        assert uow.merchants.find_by_phone(world.user(ADMIN_PHONE).phone) is None
    assert world.core.catalog.list_all() == []


def test_apparel_profile_has_one_store_and_no_driver() -> None:
    world = World()
    opened = world.http.open_shop.execute(
        world.admin, OpenShopCommand(**{**_base(), "profile_code": "apparel", "name": "Mode"})
    )
    with world.core.shop_uow_factory(opened.shop_id) as uow:
        assert [loc.name for loc in LocationRepository.within(uow).list_all()] == ["Boutique"]
    assert world.journal(opened.shop_id, AuditQuery(modules=frozenset({"platform"})))


def _base() -> dict[str, str]:
    return {
        "profile_code": "motos",
        "name": "Motos Garoua",
        "city": "Garoua",
        "phone": "222000000",
        "owner_name": "Moussa",
        "owner_phone": OWNER_PHONE,
    }
