"""T27 — ouverture Prêt-à-porter / Textile (PRF-01, 02, 04) et `ChangeShopProfile` (PRF-06 à 08)."""

import pytest

from app.application.audit.ports import AuditQuery
from app.application.catalog.use_cases.context import ArticleInput
from app.application.catalog.use_cases.create_article import CreateArticleCommand
from app.application.security.errors import PlatformAdminRequired
from app.application.shops.ports import (
    ExpenseCategoryRepository,
    LocationRepository,
    PaymentModeRepository,
    ShopSettingsRepository,
)
from app.application.shops.use_cases.open_shop import OpenedShop, OpenShopCommand
from app.domain.profiles.apparel import APPAREL
from app.domain.profiles.modules import UPCOMING_MODULES, Module
from app.domain.profiles.printing import ReceiptFormat
from app.domain.profiles.registry import profile_for
from app.domain.shared.errors import NotFound
from app.domain.shared.ids import ShopId
from app.domain.shared.roles import Role
from app.domain.shops.errors import ProfileChangeBlocked, RoleNotOffered, UnknownProfile
from app.domain.shops.location import Location
from tests.application.catalog.support import CatalogWorld
from tests.application.shops.support import World


def open_profile(world: World, code: str, owner_phone: str = "690000009") -> OpenedShop:
    command = OpenShopCommand(
        profile_code=code,
        name=f"Boutique {code}",
        city="Douala",
        phone="233000000",
        owner_name="Awa",
        owner_phone=owner_phone,
    )
    return world.http.open_shop.execute(world.admin, command)


def locations(world: World, shop_id: ShopId) -> list[Location]:
    with world.core.shop_uow_factory(shop_id) as uow:
        return LocationRepository.within(uow).list_all()


@pytest.mark.parametrize("code", ["apparel", "textile"])
def test_prf01_02_apparel_and_textile_open_with_one_store(code: str) -> None:
    world = World()
    opened = open_profile(world, code)
    profile = profile_for(code)
    (store,) = locations(world, opened.shop_id)
    assert (store.name, store.details.is_point_of_sale, store.active) == ("Boutique", True, True)
    with world.core.shop_uow_factory(opened.shop_id) as uow:
        settings = ShopSettingsRepository.within(uow).current().values
    assert settings.receipt_format is ReceiptFormat.MM58
    assert (settings.paper_width_mm, settings.exchange_days) == (58, 7)
    assert settings.reception_location_id == store.id  # QC-5 : achats reçus à « Boutique »
    assert profile.roles == (Role.OWNER, Role.SELLER, Role.ACCOUNTANT)
    assert profile.role_label(Role.SELLER) == "Employé"
    summary = world.http.platform.get(world.admin, opened.shop_id)
    assert summary.enabled_modules == profile.modules <= profile.available_modules
    assert Module.TRANSPORT not in profile.available_modules
    assert not summary.enabled_modules & UPCOMING_MODULES  # jamais activés
    expected_units = ["PIECE"] if code == "apparel" else ["METER", "PIECE"]
    assert [unit.value for unit in profile.stock_units] == expected_units
    with pytest.raises(RoleNotOffered):  # PRF-04
        world.add(world.owner(opened), "677000004", Role.DRIVER)


def test_prf06_an_empty_motos_shop_becomes_apparel() -> None:
    world = World()
    opened = world.open_motos()
    summary = world.http.change_profile.execute(world.admin, opened.shop_id, "apparel")
    assert summary.profile_code.value == "apparel"
    assert summary.enabled_modules == APPAREL.modules
    by_name = {loc.name: loc for loc in locations(world, opened.shop_id)}
    assert {name: loc.active for name, loc in by_name.items()} == {
        "Garoua-Boulaï": False,
        "Ngaoundéré": False,
        "Garoua": False,
        "Boutique": True,
    }
    with world.core.shop_uow_factory(opened.shop_id) as uow:
        settings = ShopSettingsRepository.within(uow).current().values
        modes = PaymentModeRepository.within(uow).list_all()
        categories = ExpenseCategoryRepository.within(uow).list_all()
    assert settings.receipt_format is ReceiptFormat.MM58
    assert settings.exchange_days == 7
    assert settings.reception_location_id == by_name["Boutique"].id
    assert (len(modes), len(categories)) == (6, 5)  # rien en double
    platform = world.journal(opened.shop_id, AuditQuery(modules=frozenset({"platform"})))
    changed = [e for e in platform if e.summary.startswith("Type de boutique")]
    assert len(changed) == 1
    assert changed[0].sensitive
    written = len(world.journal(opened.shop_id))
    assert world.http.change_profile.execute(world.admin, opened.shop_id, "apparel") == summary
    assert len(world.journal(opened.shop_id)) == written  # même type : rien n'est écrit


def test_same_profile_writes_nothing() -> None:
    world = World()
    opened = world.open_motos()
    before = len(world.journal(opened.shop_id))
    world.http.change_profile.execute(world.admin, opened.shop_id, "motos")
    assert len(world.journal(opened.shop_id)) == before


def test_prf07_an_article_blocks_the_change_and_nothing_is_written() -> None:
    world = CatalogWorld()
    owner = world.motos_owner()
    shop_id = World.shop_of(owner)
    data = ArticleInput(fields={"brand": "Haojue", "model": "HJ125-8"})
    world.catalog.create.execute(owner, CreateArticleCommand(data=data))
    before = len(world.journal(shop_id))
    with pytest.raises(ProfileChangeBlocked) as caught:
        world.http.change_profile.execute(world.admin, shop_id, "apparel")
    assert caught.value.details["blocking"] == {"articles": 1}
    assert world.http.platform.get(world.admin, shop_id).profile_code.value == "motos"
    assert [loc.active for loc in locations(world, shop_id)] == [True, True, True]
    assert len(world.journal(shop_id)) == before


def test_prf07_a_driver_member_blocks_the_change() -> None:
    world = World()
    opened = world.open_motos()
    world.member(world.owner(opened), "677000004", Role.DRIVER)
    with pytest.raises(ProfileChangeBlocked) as caught:
        world.http.change_profile.execute(world.admin, opened.shop_id, "textile")
    assert caught.value.details["blocking"] == {"members": 1}


def test_a_seller_keeps_his_usual_location() -> None:
    world = World()
    opened = world.open_motos()
    world.member(world.owner(opened), "677000002", Role.SELLER, "Garoua")
    world.http.change_profile.execute(world.admin, opened.shop_id, "apparel")
    active = sorted(loc.name for loc in locations(world, opened.shop_id) if loc.active)
    assert active == ["Boutique", "Garoua"]


def test_prf08_admin_only_known_profile_and_shop() -> None:
    world = World()
    opened = world.open_motos()
    with pytest.raises(PlatformAdminRequired):
        world.http.change_profile.execute(world.owner(opened), opened.shop_id, "apparel")
    with pytest.raises(UnknownProfile):
        world.http.change_profile.execute(world.admin, opened.shop_id, "epicerie")
    with pytest.raises(NotFound):
        world.http.change_profile.execute(world.admin, ShopId.new(), "apparel")
    assert world.http.platform.get(world.admin, opened.shop_id).profile_code.value == "motos"
