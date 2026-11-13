"""Changement de type (QC-1, T27) : boutique vide exigée, plan des lieux, `Shop.change_profile`."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.domain.audit.values import Performer
from app.domain.profiles.apparel import APPAREL, TEXTILE
from app.domain.profiles.modules import UPCOMING_MODULES, Module
from app.domain.profiles.motos import MOTOS
from app.domain.profiles.profile import ProfileCode
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.shared.roles import Role
from app.domain.shops.errors import ProfileChangeBlocked
from app.domain.shops.events import ShopProfileChanged
from app.domain.shops.ids import LocationId, MembershipId, MerchantAccountId
from app.domain.shops.location import Location, LocationDetails
from app.domain.shops.membership import Membership
from app.domain.shops.profile_change import (
    DATA_KINDS,
    BlockingKind,
    locations_in_use,
    plan_locations,
    require_empty,
)
from app.domain.shops.values import LocationKind
from tests.contracts.shop_data import shop

NOW = datetime(2026, 11, 13, 9, 0, tzinfo=UTC)
WHO = Performer(UserId.new(), "admin", DeviceId.new())
SHOP = ShopId.new()
EMPTY = dict.fromkeys(DATA_KINDS, 0)


def member(role: Role, *, location: LocationId | None = None, active: bool = True) -> Membership:
    return Membership(
        id=MembershipId.new(),
        shop_id=SHOP,
        user_id=UserId.new(),
        role=role,
        default_location_id=location,
        active=active,
    )


def motos_locations() -> list[Location]:
    return [
        Location.seed(
            SHOP,
            LocationDetails(
                name=t.name,
                kind=t.kind,
                is_point_of_sale=t.is_point_of_sale,
                city=t.city,
                display_order=t.display_order,
            ),
        )
        for t in MOTOS.locations
    ]


def test_an_empty_shop_may_change() -> None:
    require_empty(EMPTY, [member(Role.OWNER), member(Role.ACCOUNTANT)], APPAREL)


def test_blocking_lists_each_non_zero_kind_in_order() -> None:
    counts = {**EMPTY, BlockingKind.SALES: 2, BlockingKind.ARTICLES: 1}
    driver = member(Role.DRIVER, active=False)  # même inactif : réactivable, donc bloquant
    with pytest.raises(ProfileChangeBlocked) as caught:
        require_empty(counts, [member(Role.OWNER), driver], APPAREL)
    assert caught.value.code == "PROFILE_CHANGE_BLOCKED"
    assert list(caught.value.details["blocking"]) == ["articles", "sales", "members"]  # type: ignore[call-overload]
    assert caught.value.details == {
        "blocking": {"articles": 1, "sales": 2, "members": 1},
        "profile": "apparel",
    }
    require_empty(EMPTY, [driver], MOTOS)  # Motos propose le Chauffeur


def test_an_incomplete_or_invalid_census_fails_fast() -> None:
    partial = {BlockingKind.ARTICLES: 0}
    with pytest.raises(ValueError, match="incomplet"):
        require_empty(partial, [], APPAREL)
    for wrong in (-1, True, 1.0):
        with pytest.raises(ValueError, match="invalide"):
            require_empty({**EMPTY, BlockingKind.EXPENSES: wrong}, [], APPAREL)  # type: ignore[dict-item]


def test_motos_to_apparel_creates_the_store_and_deactivates_the_rest() -> None:
    plan = plan_locations(motos_locations(), APPAREL, frozenset())
    assert [(d.name, d.kind, d.is_point_of_sale) for d in plan.created] == [
        ("Boutique", LocationKind.STORE, True)
    ]
    assert sorted((loc.name, d.active) for loc, d in plan.changed) == [
        ("Garoua", False),
        ("Garoua-Boulaï", False),
        ("Ngaoundéré", False),
    ]


def test_a_location_in_use_stays_and_a_same_name_location_is_taken_over() -> None:
    existing = motos_locations()
    garoua = next(loc for loc in existing if loc.name == "Garoua")
    old_store = Location.seed(
        SHOP, LocationDetails(name="boutique", kind=LocationKind.WAREHOUSE,
                              is_point_of_sale=False, active=False)
    )  # fmt: skip
    seller = member(Role.SELLER, location=garoua.id, active=False)
    plan = plan_locations([*existing, old_store], APPAREL, locations_in_use([seller]))
    assert plan.created == ()
    changed = {loc.name: d for loc, d in plan.changed}
    assert set(changed) == {"boutique", "Garoua-Boulaï", "Ngaoundéré"}
    taken = changed["boutique"]
    assert (taken.name, taken.kind, taken.is_point_of_sale, taken.active) == (
        "Boutique", LocationKind.STORE, True, True,
    )  # fmt: skip


def test_same_details_are_left_untouched() -> None:
    store = plan_locations([], TEXTILE, frozenset()).created[0]
    assert plan_locations([Location.seed(SHOP, store)], APPAREL, frozenset()).changed == ()
    inactive = Location.seed(SHOP, replace(store, name="Ancien", active=False))
    plan = plan_locations([Location.seed(SHOP, store), inactive], APPAREL, frozenset())
    assert plan.changed == ()  # un lieu déjà inactif n'est pas réécrit


def test_shop_change_profile_is_sensitive_and_sets_the_profile_modules() -> None:
    motos = shop(SHOP, MerchantAccountId.new())
    assert motos.change_profile(MOTOS, performer=WHO, now=NOW) is False
    assert motos.change_profile(APPAREL, performer=WHO, now=NOW) is True
    assert motos.profile_code is ProfileCode.APPAREL
    assert motos.enabled_modules == APPAREL.modules
    assert Module.TRANSPORT not in motos.enabled_modules
    assert not motos.enabled_modules & UPCOMING_MODULES
    (event,) = motos.events.pull()
    assert isinstance(event, ShopProfileChanged)
    record = event.audit_record()
    assert (record.sensitive, record.module, record.action.value) == (True, "platform", "configure")
    assert {c.field for c in record.changes} >= {"profile_code"}
    assert record.summary == "Type de boutique changé : Prêt-à-porter"
