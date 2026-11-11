"""Agrégats du socle : règles locales, événements journalisables, cas limites."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from app.domain.audit.values import AuditAction, EntityRef, FieldChange, Performer
from app.domain.identity.phone import PhoneNumber
from app.domain.profiles.modules import Module
from app.domain.profiles.motos import MOTOS
from app.domain.shared.errors import Duplicate, InvalidStateTransition, ValidationFailed
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.roles import Role
from app.domain.shops.account import MerchantAccount
from app.domain.shops.admin_grant import AdminAccessGrant
from app.domain.shops.events import ShopAuditedEvent, diff
from app.domain.shops.expense_category import ExpenseCategory
from app.domain.shops.ids import MembershipId, MerchantAccountId
from app.domain.shops.location import Location, LocationDetails
from app.domain.shops.membership import Membership
from app.domain.shops.settings import SettingsValues
from app.domain.shops.shop import Shop, ShopIdentity
from app.domain.shops.values import LocationKind, ShopStatus, clean_optional, require_int

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)
WHO = Performer(UserId.new(), "owner")
REF = EntityRef("shop")


def test_account_keeps_shop_names_unique() -> None:
    account = MerchantAccount.create(name="Moussa", phone=PhoneNumber.parse("690000001"))
    shop = ShopId.new()
    account.register_shop(shop, "Motos Garoua")
    with pytest.raises(Duplicate):
        account.register_shop(ShopId.new(), "MOTOS garoua")
    with pytest.raises(Duplicate):
        account.register_shop(shop, "Autre")
    with pytest.raises(TypeError):
        MerchantAccount(id=MerchantAccountId.new(), name="X", phone="690")  # type: ignore[arg-type]  # type faux testé


def test_shop_administration_and_header() -> None:
    identity = ShopIdentity(name="Motos", city="Garoua", phone=PhoneNumber.parse("222000000"))
    shop = Shop.open(
        shop_id=ShopId.new(),
        account_id=MerchantAccountId.new(),
        profile_code=MOTOS.code,
        identity=identity,
        modules=MOTOS.modules,
        performer=WHO,
        now=NOW,
    )
    assert not shop.administer(
        modules=None, status=None, available=MOTOS.available_modules, performer=WHO, now=NOW
    )
    assert shop.administer(
        modules=[Module.SALES], status=ShopStatus.CLOSED, available=MOTOS.available_modules,
        performer=WHO, now=NOW,
    )  # fmt: skip
    assert Module.CORE in shop.enabled_modules
    assert shop.status is ShopStatus.CLOSED
    with pytest.raises(ValidationFailed):
        shop.update_identity(replace(identity, name="Autre"), performer=WHO, now=NOW)
    assert not shop.update_identity(identity, performer=WHO, now=NOW)
    assert shop.update_identity(replace(identity, niu="M0123"), performer=WHO, now=NOW)
    events = shop.events.pull()
    assert [e.audit_record().action for e in events if isinstance(e, ShopAuditedEvent)] == [
        AuditAction.CREATE, AuditAction.CONFIGURE, AuditAction.CONFIGURE,
    ]  # fmt: skip
    with pytest.raises(ValueError, match="Socle"):
        replace(shop, enabled_modules=frozenset({Module.SALES}))


def test_membership_state_rules() -> None:
    membership = Membership(
        id=MembershipId.new(), shop_id=ShopId.new(), user_id=UserId.new(), role=Role.ACCOUNTANT
    )
    with pytest.raises(InvalidStateTransition):
        membership.set_active(True, performer=WHO, now=NOW)
    with pytest.raises(ValueError, match="vendeur"):
        Membership(
            id=MembershipId.new(), shop_id=ShopId.new(), user_id=UserId.new(), role=Role.SELLER
        )
    assert not membership.assign(Role.ACCOUNTANT, None, profile=MOTOS, performer=WHO, now=NOW)


def test_settings_values_bounds() -> None:
    base = SettingsValues(
        receipt_format="80mm",  # type: ignore[arg-type]  # converti en ReceiptFormat
        paper_width_mm=80, printable_width_mm=72, margin_mm=3, font_size_pt=10, show_logo=True,
    )  # fmt: skip
    for bad in (
        {"low_stock_threshold": Decimal("2.55")},
        {"low_stock_threshold": Decimal(-1)},
        {"min_price_enabled": "non"},
        {"exchange_days": 400},
        {"truck_silent_hours": 0},
    ):
        with pytest.raises(ValidationFailed):
            replace(base, **bad)
    with pytest.raises(TypeError):
        replace(base, reception_location_id="garoua")  # type: ignore[arg-type]  # type faux testé
    assert base.scalars()["low_stock_threshold"] == "2.0"


def test_grant_lifecycle() -> None:
    grant = AdminAccessGrant.grant(shop_id=ShopId.new(), performer=WHO, now=NOW)
    assert grant.is_active(NOW)
    assert not grant.is_active(NOW + timedelta(hours=24))
    grant.revoke(performer=WHO, now=NOW)
    with pytest.raises(InvalidStateTransition):
        grant.revoke(performer=WHO, now=NOW)
    with pytest.raises(ValueError, match="Durée"):
        AdminAccessGrant.grant(shop_id=ShopId.new(), performer=WHO, now=NOW, duration=timedelta(0))
    with pytest.raises(ValueError, match="expire"):
        replace(grant, expires_at=NOW)


def test_small_values_and_events() -> None:
    assert clean_optional("  ", "f") is None
    with pytest.raises(ValidationFailed):
        require_int(True, "copies", low=1, high=3)
    with pytest.raises(ValueError, match="différents"):
        diff({"a": 1}, {"b": 1})
    assert diff({"a": 1, "b": 2}, {"a": 1, "b": 3}) == (FieldChange("b", 2, 3),)
    with pytest.raises(TypeError, match="abstraite"):
        ShopAuditedEvent(
            shop_id=ShopId.new(), occurred_at=NOW, performer=WHO, entity=REF, summary="x"
        )
    with pytest.raises(ValueError, match="base"):
        ExpenseCategory(id=ExpenseCategory.seed_base(ShopId.new(), "Repas", 1).id,
                        shop_id=ShopId.new(), name="Repas", is_base=True, active=False)  # fmt: skip
    with pytest.raises(TypeError):
        LocationDetails(name="X", kind=LocationKind.STORE, is_point_of_sale=1)  # type: ignore[arg-type]  # type faux testé
    raw_kind: Any = "store"  # saisie brute : convertie en LocationKind
    location = Location.seed(
        ShopId.new(), LocationDetails(name="X", kind=raw_kind, is_point_of_sale=False)
    )
    assert location.details.kind is LocationKind.STORE
    assert not location.events.pull()
