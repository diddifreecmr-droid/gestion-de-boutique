"""Contrat des dépôts du socle (T10) : aller-retour, unicités nommées, listes, isolation."""

from decimal import Decimal

import pytest

from app.application.shops.ports import (
    AdminGrantRepository,
    ExpenseCategoryRepository,
    LocationRepository,
    MembershipRepository,
    PaymentModeRepository,
    ShopRepository,
    ShopSettingsRepository,
)
from app.domain.audit.values import Performer
from app.domain.shared.errors import Duplicate, NotFound
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.roles import Role
from app.domain.shops.admin_grant import AdminAccessGrant
from app.domain.shops.expense_category import ExpenseCategory
from app.domain.shops.ids import MembershipId, MerchantAccountId
from app.domain.shops.membership import Membership
from app.domain.shops.payment_mode import PaymentMode, PaymentModeDetails
from app.domain.shops.settings import ShopSettings
from tests.contracts.backends import ContractBackend
from tests.contracts.helpers import run_in_uow
from tests.contracts.shop_data import NOW, seed_shop_and_settings, store


def test_shop_settings_and_location_round_trip(backend: ContractBackend, shop_a: ShopId) -> None:
    account = MerchantAccountId.new()
    with backend.uow(shop_a) as uow:
        location = seed_shop_and_settings(uow, account)
        uow.commit()
    with backend.uow(shop_a) as uow:
        shop = ShopRepository.within(uow).current()
        settings = ShopSettingsRepository.within(uow).current()
        [read] = LocationRepository.within(uow).list_all()
    assert (shop.account_id, shop.identity.niu, shop.enabled_modules) == (
        account,
        "M01",
        shop.enabled_modules,
    )
    assert settings.values.reception_location_id == location.id
    assert settings.values.low_stock_threshold == Decimal(2)
    assert read.details == location.details
    assert read.version == 1
    with backend.uow(shop_a) as uow, pytest.raises(Duplicate) as caught:
        ShopSettingsRepository.within(uow).add(ShopSettings.seed(shop_a, settings.values))
    assert caught.value.details["constraint"] == "shop_settings_shop"


def test_names_are_unique_without_case(backend: ContractBackend, shop_a: ShopId) -> None:
    with backend.uow(shop_a) as uow:
        LocationRepository.within(uow).add(store(shop_a, "Garoua"))
        PaymentModeRepository.within(uow).add(
            PaymentMode.seed(shop_a, PaymentModeDetails(name="Wave", reference_required=True))
        )
        ExpenseCategoryRepository.within(uow).add(ExpenseCategory.seed_base(shop_a, "Repas", 1))
        uow.commit()
    clashes = [
        (LocationRepository, store(shop_a, "GAROUA"), "location_name"),
        (
            PaymentModeRepository,
            PaymentMode.seed(shop_a, PaymentModeDetails(name="wave", reference_required=False)),
            "payment_mode_name",
        ),
        (
            ExpenseCategoryRepository,
            ExpenseCategory.seed_base(shop_a, "REPAS", 2),
            "expense_category_name",
        ),
    ]
    for port, aggregate, constraint in clashes:
        with pytest.raises(Duplicate) as caught:
            run_in_uow(backend, shop_a, lambda uow, p=port, a=aggregate: p.within(uow).add(a))  # type: ignore[misc]  # ports hétérogènes
        assert caught.value.details["constraint"] == constraint
    with backend.uow(shop_a) as uow:
        assert [m.name for m in PaymentModeRepository.within(uow).list_all()] == ["Wave"]
        assert [c.name for c in ExpenseCategoryRepository.within(uow).list_all()] == ["Repas"]


def test_memberships_and_grants(backend: ContractBackend, shop_a: ShopId, shop_b: ShopId) -> None:
    user = UserId.new()
    location = store(shop_a)
    seller = Membership(
        id=MembershipId.new(),
        shop_id=shop_a,
        user_id=user,
        role=Role.SELLER,
        default_location_id=location.id,
    )
    grant = AdminAccessGrant.grant(shop_id=shop_a, performer=Performer(user, "owner"), now=NOW)
    grant.events.pull()
    with backend.uow(shop_a) as uow:
        MembershipRepository.within(uow).add(seller)
        AdminGrantRepository.within(uow).add(grant)
        uow.commit()
    with backend.uow(shop_a) as uow:
        memberships = MembershipRepository.within(uow)
        found = memberships.find_by_user(user)
        assert found is not None
        assert found.default_location_id == location.id
        assert memberships.find_by_user(UserId.new()) is None
        assert [m.id for m in memberships.list_all()] == [seller.id]
        active = AdminGrantRepository.within(uow).active(NOW)
        assert active is not None
        assert active.expires_at == grant.expires_at
        assert AdminGrantRepository.within(uow).active(grant.expires_at) is None
    twin = Membership(id=MembershipId.new(), shop_id=shop_a, user_id=user, role=Role.OWNER)
    with pytest.raises(Duplicate) as caught:
        run_in_uow(backend, shop_a, lambda uow: MembershipRepository.within(uow).add(twin))
    assert caught.value.details["constraint"] == "membership_user"
    with backend.uow(shop_b) as uow:
        assert MembershipRepository.within(uow).list_all() == []
        assert MembershipRepository.within(uow).find(seller.id) is None
        with pytest.raises(NotFound):
            ShopSettingsRepository.within(uow).current()
