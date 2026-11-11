"""Contrat du module Dépenses (T18) : aller-retour, unicités, isolation, verrou, requête.

Rejoué sur l'adaptateur mémoire, sur SQLite (`tests/infrastructure/sqlalchemy`) et sur
PostgreSQL (`--backend=postgres`).
"""

from dataclasses import replace
from datetime import timedelta
from functools import partial

import pytest

from app.application.expenses.ports import (
    ExpenseFilters,
    ExpenseQuery,
    ExpenseRepository,
    TagRepository,
)
from app.application.ports.pagination import PageRequest
from app.application.ports.uow import UnitOfWork
from app.application.shops.ports import ExpenseCategoryRepository
from app.domain.expenses.expense import Expense
from app.domain.expenses.ids import AttachmentId
from app.domain.expenses.tag import Tag, tag_key
from app.domain.shared.errors import Duplicate, NotFound, VersionConflict
from app.domain.shared.ids import ShopId
from app.domain.shops.expense_category import ExpenseCategory
from app.domain.shops.ids import LocationId
from tests.contracts.backends import ContractBackend
from tests.contracts.expense_data import (
    DAY,
    OTHER_CATEGORY,
    WHO_PERFORMER,
    T,
    expense,
    tag,
)
from tests.contracts.helpers import run_in_uow

PERIOD = ExpenseFilters(first_day=DAY, last_day=DAY)


def test_expense_round_trip_with_tags_and_cancellation(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    first, second = tag(shop_a, "Groupe"), tag(shop_a, "Fête")
    recorded = expense(shop_a, 1, tags=(second.id, first.id))
    recorded.details = replace(
        recorded.details,
        description="Plein",
        location_id=LocationId.new(),
        beneficiary="Ali",
        attachment_id=AttachmentId.new(),
    )
    with backend.uow(shop_a) as uow:
        TagRepository.within(uow).add(first)
        TagRepository.within(uow).add(second)
        ExpenseRepository.within(uow).add(recorded)
        uow.commit()
    with backend.uow(shop_a) as uow:
        read = ExpenseRepository.within(uow).get(recorded.id)
        read.cancel("Doublon", performer=WHO_PERFORMER, now=T + timedelta(hours=1))
        read.retag(first.id, second.id)
        ExpenseRepository.within(uow).update(read)
        uow.commit()
    with backend.uow(shop_a) as uow:
        again = ExpenseRepository.within(uow).get(recorded.id)
    assert again.details == replace(recorded.details, tag_ids=(second.id,))
    assert again.capture == recorded.capture
    assert again.cancellation == read.cancellation
    assert (again.number, again.version) == (recorded.number, 2)


def test_number_and_tag_name_are_unique_per_shop(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    run_in_uow(backend, shop_a, lambda uow: ExpenseRepository.within(uow).add(expense(shop_a, 1)))
    run_in_uow(backend, shop_a, lambda uow: TagRepository.within(uow).add(tag(shop_a, "Groupe")))
    with pytest.raises(Duplicate) as caught:
        run_in_uow(
            backend, shop_a, lambda uow: ExpenseRepository.within(uow).add(expense(shop_a, 1))
        )
    assert caught.value.details["constraint"] == "expense_number"
    for name in ("GROUPE", " groupe "):
        clashing = tag(shop_a, name)
        with pytest.raises(Duplicate) as clash:
            run_in_uow(backend, shop_a, partial(add_tag, clashing))
        assert clash.value.details["constraint"] == "tag_name"
    run_in_uow(backend, shop_b, lambda uow: TagRepository.within(uow).add(tag(shop_b, "groupe")))
    run_in_uow(backend, shop_b, lambda uow: ExpenseRepository.within(uow).add(expense(shop_b, 1)))
    with backend.uow(shop_a) as uow:
        tags = TagRepository.within(uow)
        found = tags.find_by_key(tag_key("GROUPE"))
        assert found is not None
        assert found.name == "Groupe"
        assert tags.find_by_key("absent") is None
        assert [t.name for t in tags.list_all()] == ["Groupe"]


def add_tag(label: Tag, uow: UnitOfWork) -> None:
    TagRepository.within(uow).add(label)


def test_shops_are_isolated(backend: ContractBackend, shop_a: ShopId, shop_b: ShopId) -> None:
    label = tag(shop_a, "Groupe")
    recorded = expense(shop_a, 1, tags=(label.id,))
    with backend.uow(shop_a) as uow:
        TagRepository.within(uow).add(label)
        ExpenseRepository.within(uow).add(recorded)
        uow.commit()
    with backend.uow(shop_b) as uow:
        with pytest.raises(NotFound):
            ExpenseRepository.within(uow).get(recorded.id)
        assert TagRepository.within(uow).find(label.id) is None
        assert ExpenseRepository.within(uow).list_with_tag(label.id) == []
        assert list(ExpenseQuery.within(uow).search(PERIOD, PageRequest()).items) == []
        assert ExpenseQuery.within(uow).totals(PERIOD).amount == 0
    with backend.uow(shop_a) as uow:
        [tagged] = ExpenseRepository.within(uow).list_with_tag(label.id)
    assert tagged.id == recorded.id


def test_optimistic_lock(backend: ContractBackend, shop_a: ShopId) -> None:
    recorded = expense(shop_a, 1)
    run_in_uow(backend, shop_a, lambda uow: ExpenseRepository.within(uow).add(recorded))
    stale, fresh = (read(backend, shop_a, recorded) for _ in range(2))
    fresh.details = replace(fresh.details, amount=2_000)
    run_in_uow(backend, shop_a, lambda uow: ExpenseRepository.within(uow).update(fresh))
    stale.details = replace(stale.details, amount=3_000)
    with pytest.raises(VersionConflict):
        run_in_uow(backend, shop_a, lambda uow: ExpenseRepository.within(uow).update(stale))
    assert read(backend, shop_a, recorded).details.amount == 2_000


def read(backend: ContractBackend, shop_id: ShopId, recorded: Expense) -> Expense:
    with backend.uow(shop_id) as uow:
        return ExpenseRepository.within(uow).get(recorded.id)


def test_query_filters_paginates_and_excludes_cancelled_from_totals(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    label = tag(shop_a, "Groupe")
    old = expense(shop_a, 1, amount=100, spent_on=DAY - timedelta(days=1))
    fuel = expense(shop_a, 2, amount=2_000, tags=(label.id,), minutes=1)
    meal = expense(shop_a, 3, amount=500, category=OTHER_CATEGORY, minutes=2)
    void = expense(shop_a, 4, amount=9_999, tags=(label.id,), minutes=3)
    void.cancel("Erreur", performer=WHO_PERFORMER, now=T)
    with backend.uow(shop_a) as uow:
        TagRepository.within(uow).add(label)
        for item in (old, fuel, meal, void):
            ExpenseRepository.within(uow).add(item)
        uow.commit()
    with backend.uow(shop_a) as uow:
        query = ExpenseQuery.within(uow)
        page = query.search(PERIOD, PageRequest(limit=2))
        assert [e.number for e in page.items] == [void.number, meal.number]
        assert page.next_cursor is not None
        rest = query.search(PERIOD, PageRequest(limit=2, after=page.next_cursor))
        assert [e.number for e in rest.items] == [fuel.number]
        assert rest.next_cursor is None
        assert rest.items[0].details.tag_ids == (label.id,)
        totals = query.totals(PERIOD)
        assert (totals.amount, totals.count) == (2_500, 2)
        assert [(t.category_id, t.amount, t.count) for t in totals.by_category] == [
            (fuel.details.category_id, 2_000, 1),
            (OTHER_CATEGORY, 500, 1),
        ]
        tagged = replace(PERIOD, tag_id=label.id)
        assert [e.number for e in query.search(tagged, PageRequest()).items] == [
            void.number,
            fuel.number,
        ]
        assert query.totals(tagged).amount == 2_000
        wide = replace(PERIOD, first_day=DAY - timedelta(days=1), category_id=OTHER_CATEGORY)
        assert query.totals(wide).amount == 500
        none = replace(PERIOD, created_by=WHO_PERFORMER.user_id, payment_mode_id=None)
        assert query.totals(none).count == 2


def test_category_keeps_requires_description(backend: ContractBackend, shop_a: ShopId) -> None:
    other = ExpenseCategory.seed_base(shop_a, "Autre", 5)
    run_in_uow(backend, shop_a, lambda uow: ExpenseCategoryRepository.within(uow).add(other))
    with backend.uow(shop_a) as uow:
        categories = ExpenseCategoryRepository.within(uow)
        read = categories.get(other.id)
        assert read.requires_description
        read.change(performer=WHO_PERFORMER, now=T, name="Divers")
        categories.update(read)
        uow.commit()
    with backend.uow(shop_a) as uow:
        renamed = ExpenseCategoryRepository.within(uow).get(other.id)
    assert (renamed.name, renamed.requires_description, renamed.version) == ("Divers", True, 2)
