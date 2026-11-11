"""UC-DEP-02, 03, 05 — catégories, tags et fusion, filtres, « Refaire » (EXP-03/04/05/07)."""

from datetime import date, timedelta

import pytest

from app.application.expenses.use_cases.list_expenses import ExpenseCriteria
from app.application.expenses.use_cases.manage_expense_categories import CategoryPatch
from app.application.ports.pagination import PageRequest
from app.application.security.errors import PermissionDenied
from app.domain.expenses.errors import BaseCategoryLocked, InvalidTagMerge
from app.domain.shared.errors import Duplicate, ValidationFailed
from tests.application.expenses.support import Shop

TODAY = date(2026, 11, 11)


def test_categories_base_locked_added_deactivable_owner_only() -> None:
    shop = Shop()
    base = shop.uc.categories.list(shop.owner)
    assert [c.name for c in base] == ["Carburant", "Repas", "Salaire", "Loyer", "Autre"]
    assert [c.requires_description for c in base] == [False] * 4 + [True]
    rent = base[3]
    renamed = shop.uc.categories.update(shop.owner, rent.id, CategoryPatch(name="Loyers"), 1)
    assert renamed.name == "Loyers"
    with pytest.raises(BaseCategoryLocked):
        shop.uc.categories.update(shop.owner, rent.id, CategoryPatch(active=False), 2)
    added, created = shop.uc.categories.create(shop.owner, "Électricité")
    assert created
    assert added.display_order == 6
    replay, created_again = shop.uc.categories.create(shop.owner, "x", category_id=added.id)
    assert (replay.id, created_again) == (added.id, False)
    with pytest.raises(Duplicate):
        shop.uc.categories.create(shop.owner, "électricité")
    off = shop.uc.categories.update(shop.owner, added.id, CategoryPatch(active=False), 1)
    assert not off.active
    assert shop.uc.categories.update(shop.owner, added.id, CategoryPatch(), 2).version == 2
    assert "Électricité" not in [c.name for c in shop.uc.categories.list(shop.accountant)]
    assert "Électricité" in [c.name for c in shop.uc.categories.list(shop.owner)]
    with pytest.raises(PermissionDenied):
        shop.uc.categories.create(shop.accountant, "Divers")
    with pytest.raises(PermissionDenied):
        shop.uc.categories.update(shop.accountant, added.id, CategoryPatch(name="Y"), 2)
    with pytest.raises(PermissionDenied):
        shop.uc.categories.list(shop.seller)


def test_merge_retags_expenses_and_merges_totals() -> None:
    shop = Shop()
    short = shop.record(shop.accountant, 10_000, tag_names=("Groupe",))
    long = shop.record(shop.accountant, 20_000, tag_names=("Groupe électrogène", "Fête"))
    group, generator = short.tags[0], long.tags[0]
    shop.record(shop.accountant, 5_000, tag_names=("Divers",))
    with pytest.raises(PermissionDenied):
        shop.uc.merge_tags.execute(shop.accountant, group.id, generator.id)
    result = shop.uc.merge_tags.execute(shop.owner, group.id, generator.id)
    assert (result.target.id, result.retagged_expenses) == (generator.id, 1)
    assert [t.name for t in shop.uc.tags.execute(shop.accountant)] == [
        "Divers",
        "Fête",
        "Groupe électrogène",
    ]
    assert [t.name for t in shop.uc.tags.execute(shop.accountant, "GROUPE")] == [
        "Groupe électrogène"
    ]
    by_tag = shop.listing(tag_id=generator.id)
    assert (by_tag.totals.amount, len(by_tag.items)) == (30_000, 2)
    assert shop.listing(tag_id=group.id).totals.amount == 30_000  # l'ancien tag suit la cible
    retyped = shop.record(shop.owner, 1_000, tag_names=("groupe",))
    assert [t.id for t in retyped.tags] == [generator.id]
    with pytest.raises(InvalidTagMerge):
        shop.uc.merge_tags.execute(shop.owner, group.id, generator.id)
    divers = shop.uc.tags.execute(shop.owner, "divers")[0]
    shop.uc.merge_tags.execute(shop.owner, generator.id, divers.id)
    assert shop.listing(tag_id=divers.id).totals.amount == 36_000
    retyped_again = shop.record(shop.owner, 1, tag_names=("Groupe",))
    assert [t.id for t in retyped_again.tags] == [divers.id]  # chaîne aplatie
    with pytest.raises(PermissionDenied):
        shop.uc.tags.execute(shop.seller)


def test_list_filters_period_and_pagination() -> None:
    shop = Shop()
    yesterday = TODAY - timedelta(days=1)
    garoua = shop.world.location_id(shop.world.shop_of(shop.owner), "Garoua")
    om = shop.mode("Orange Money")
    old = shop.record(shop.accountant, 1_000, "Repas", spent_on=yesterday)
    fuel = shop.record(shop.accountant, 2_000, "Carburant", location_id=garoua)
    paid = shop.record(shop.owner, 4_000, "Carburant", payment_mode_id=om)
    assert [v.expense.id for v in shop.listing().items] == [paid.expense.id, fuel.expense.id]
    totals = shop.listing().totals
    assert (totals.amount, totals.count) == (6_000, 2)
    assert [(t.amount, t.count) for t in totals.by_category] == [(6_000, 2)]
    two_days = shop.listing(first_day=yesterday)
    assert two_days.last_day == TODAY
    assert two_days.totals.amount == 7_000
    assert shop.listing(last_day=yesterday).items[0].expense.id == old.expense.id
    assert shop.listing(location_id=garoua).totals.amount == 2_000
    assert shop.listing(created_by=shop.owner.user_id).totals.amount == 4_000
    assert shop.listing(payment_mode_id=om).totals.amount == 4_000
    assert shop.listing(category_id=shop.category("Repas")).totals.amount == 0
    first_page = shop.listing(limit=1)
    assert len(first_page.items) == 1
    assert first_page.next_cursor is not None
    rest = shop.uc.list.execute(
        shop.owner, ExpenseCriteria(), PageRequest(limit=5, after=first_page.next_cursor)
    )
    assert [v.expense.id for v in rest.items] == [fuel.expense.id]
    assert rest.next_cursor is None
    with pytest.raises(ValidationFailed, match="inversée"):
        shop.listing(first_day=TODAY, last_day=yesterday)


def test_repeat_gives_a_prefilled_draft_dated_today() -> None:
    shop = Shop()
    shop.world.clock.advance(timedelta(days=-20))
    rent = shop.record(
        shop.owner, 150_000, "Loyer", tag_names=("Boutique",), beneficiary="M. Bello"
    )
    shop.world.clock.advance(timedelta(days=20))
    view = shop.uc.repeat.execute(shop.accountant, rent.expense.id)
    draft = view.draft
    assert (draft.spent_on, draft.amount, draft.category_id, draft.beneficiary) == (
        TODAY,
        150_000,
        rent.expense.details.category_id,
        "M. Bello",
    )
    assert [t.name for t in view.tags] == ["Boutique"]
    assert str(shop.record(shop.accountant).expense.number) == "D-000002"  # rien d'écrit
    with pytest.raises(PermissionDenied):
        shop.uc.repeat.execute(shop.seller, rent.expense.id)
