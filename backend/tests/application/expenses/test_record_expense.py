"""UC-DEP-01 — Enregistrer une dépense (recette EXP-01, M23, RG-T05, RG-T09, AUD-07)."""

from datetime import date, timedelta

import pytest

from app.application.expenses.references import ExpenseInput
from app.application.expenses.use_cases.manage_expense_categories import CategoryPatch
from app.application.expenses.use_cases.record_expense import RecordExpenseCommand
from app.application.security.errors import PermissionDenied
from app.domain.audit.values import AuditAction
from app.domain.expenses.errors import DescriptionRequired, InactiveReference
from app.domain.expenses.ids import ExpenseId
from app.domain.shared.errors import DateOutOfRange, InvalidAmount, NotFound
from app.domain.shops.ids import ExpenseCategoryId
from tests.application.expenses.support import Shop
from tests.application.identity.support import T0

TODAY = date(2026, 11, 11)


def test_fuel_expense_gets_first_number_and_cash_by_default() -> None:
    shop = Shop()
    view = shop.record(shop.accountant, 25_000, "Carburant", tag_names=("Groupe",))
    expense = view.expense
    assert str(expense.number) == "D-000001"
    assert expense.details.payment_mode_id == shop.mode("Espèces")
    assert expense.details.spent_on == TODAY
    assert [tag.name for tag in view.tags] == ["Groupe"]
    assert view.editable
    capture = expense.capture
    assert (capture.created_by, capture.device_id) == (
        shop.accountant.user_id,
        shop.accountant.device_id,
    )
    assert capture.captured_at == capture.received_at == T0
    again = shop.record(shop.owner, 10_000, "Repas", tag_names=("groupe", "GROUPE "))
    assert str(again.expense.number) == "D-000002"
    assert again.expense.details.tag_ids == expense.details.tag_ids  # même tag, sans casse
    third = shop.record(shop.owner, 5_000, "Salaire")
    assert str(third.expense.number) == "D-000003"
    created = shop.world.journal(shop.world.shop_of(shop.owner))
    actions = [(e.module, e.action, e.entity.type) for e in created if e.module == "expenses"]
    assert actions.count(("expenses", AuditAction.CREATE, "expense")) == 3
    assert actions.count(("expenses", AuditAction.CREATE, "tag")) == 1


def test_other_requires_description_and_amount_must_be_positive() -> None:
    shop = Shop()
    with pytest.raises(DescriptionRequired):
        shop.record(shop.accountant, 1_000, "Autre")
    assert shop.record(shop.accountant, 1_000, "Autre", description="Ampoules").expense
    for amount in (0, -5):
        with pytest.raises(InvalidAmount):
            shop.record(shop.accountant, amount)
    assert str(shop.record(shop.accountant).expense.number) == "D-000002"  # aucun trou


def test_seller_and_driver_have_no_access() -> None:
    shop = Shop()
    for actor in (shop.seller, shop.driver):
        with pytest.raises(PermissionDenied):
            shop.record(actor)
        with pytest.raises(PermissionDenied):
            shop.listing(actor)


def test_client_id_makes_recording_idempotent() -> None:
    shop = Shop()
    expense_id = ExpenseId.new()
    first = shop.record(shop.accountant, 25_000, expense_id=expense_id)
    replay = shop.uc.record.execute
    view, created = replay(shop.accountant, _command(shop, expense_id, amount=99))
    assert not created
    assert view.expense.details.amount == 25_000
    assert view.expense.number == first.expense.number
    assert str(shop.record(shop.accountant).expense.number) == "D-000002"


def _command(shop: Shop, expense_id: ExpenseId, amount: int) -> RecordExpenseCommand:
    data = ExpenseInput(amount=amount, category_id=shop.category("Repas"))
    return RecordExpenseCommand(data=data, expense_id=expense_id)


def test_entry_date_window_rg_t09() -> None:
    shop = Shop()
    week_ago = TODAY - timedelta(days=7)
    assert shop.record(shop.accountant, spent_on=week_ago).expense.details.spent_on == week_ago
    with pytest.raises(DateOutOfRange):
        shop.record(shop.accountant, spent_on=week_ago - timedelta(days=1))
    with pytest.raises(DateOutOfRange):
        shop.record(shop.owner, spent_on=TODAY + timedelta(days=1))
    long_ago = date(2026, 1, 2)
    assert shop.record(shop.owner, spent_on=long_ago).expense.details.spent_on == long_ago


def test_device_time_is_kept_unless_far_in_the_future() -> None:
    shop = Shop()
    earlier = T0 - timedelta(minutes=3)
    view = shop.record(shop.accountant, captured_at=earlier)
    assert (view.expense.capture.captured_at, view.expense.capture.received_at) == (earlier, T0)
    with pytest.raises(DateOutOfRange):
        shop.record(shop.accountant, captured_at=T0 + timedelta(minutes=11))


def test_references_must_belong_to_the_shop_and_be_active() -> None:
    shop = Shop()
    data = ExpenseInput(amount=1, category_id=ExpenseCategoryId.new())
    with pytest.raises(NotFound):
        shop.uc.record.execute(shop.owner, RecordExpenseCommand(data=data))
    added, _ = shop.uc.categories.create(shop.owner, "Électricité")
    shop.uc.categories.update(shop.owner, added.id, CategoryPatch(active=False), added.version)
    with pytest.raises(InactiveReference):
        shop.record(shop.owner, category="Électricité")
