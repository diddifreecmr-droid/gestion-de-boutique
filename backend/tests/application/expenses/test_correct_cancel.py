"""UC-DEP-04 — Corriger ou annuler (recette EXP-06, Q-11) ; totaux hors annulées (RG-T03)."""

from datetime import UTC, date, datetime

import pytest

from app.application.security.errors import PermissionDenied
from app.domain.audit.values import AuditAction
from app.domain.expenses.errors import (
    CorrectionWindowClosed,
    InactiveReference,
    ReasonRequired,
)
from app.domain.expenses.expense import ExpenseStatus
from app.domain.shared.errors import ValidationFailed, VersionConflict
from tests.application.expenses.support import Shop

D = date(2026, 11, 10)
SAVED = datetime(2026, 11, 10, 14, 0, tzinfo=UTC)  # 15:00 à Douala
LAST_SECOND = datetime(2026, 11, 10, 22, 59, 59, tzinfo=UTC)  # 23:59:59 à Douala
MIDNIGHT = datetime(2026, 11, 10, 23, 0, tzinfo=UTC)  # 00:00:00 le 11/11 à Douala


def shop_at_d() -> Shop:
    shop = Shop()
    shop.world.clock.move_to(SAVED)
    return shop


def test_author_corrects_until_midnight_then_only_the_owner() -> None:
    shop = shop_at_d()
    view = shop.record(shop.accountant, 25_000, "Carburant")
    expense_id = view.expense.id
    shop.world.clock.move_to(LAST_SECOND)
    corrected = shop.uc.correct.execute(shop.accountant, expense_id, {"amount": 26_000}, 1)
    assert (corrected.expense.details.amount, corrected.expense.version) == (26_000, 2)
    shop.world.clock.move_to(MIDNIGHT)
    with pytest.raises(CorrectionWindowClosed):
        shop.uc.correct.execute(shop.accountant, expense_id, {"amount": 27_000}, 2)
    with pytest.raises(CorrectionWindowClosed):
        shop.uc.cancel.execute(shop.accountant, expense_id, "erreur")
    assert not shop.uc.get.execute(shop.accountant, expense_id).editable
    by_owner = shop.uc.correct.execute(shop.owner, expense_id, {"description": "Plein"}, 2)
    assert by_owner.expense.details.description == "Plein"
    assert by_owner.editable
    entries = shop.world.journal(shop.world.shop_of(shop.owner))
    updates = [e for e in entries if e.action is AuditAction.UPDATE and e.module == "expenses"]
    assert {c.field for e in updates for c in e.changes} == {"amount", "description"}


def test_accountant_cannot_touch_someone_elses_expense() -> None:
    shop = shop_at_d()
    owner_expense = shop.record(shop.owner).expense
    assert not shop.uc.get.execute(shop.accountant, owner_expense.id).editable
    with pytest.raises(PermissionDenied):
        shop.uc.correct.execute(shop.accountant, owner_expense.id, {"amount": 1}, 1)
    with pytest.raises(PermissionDenied):
        shop.uc.cancel.execute(shop.accountant, owner_expense.id, "non")
    with pytest.raises(PermissionDenied):
        shop.uc.correct.execute(shop.seller, owner_expense.id, {"amount": 1}, 1)


def test_correction_checks_version_and_rules() -> None:
    shop = shop_at_d()
    expense_id = shop.record(shop.accountant).expense.id
    with pytest.raises(VersionConflict):
        shop.uc.correct.execute(shop.accountant, expense_id, {"amount": 2}, 7)
    with pytest.raises(ValidationFailed):
        shop.uc.correct.execute(
            shop.accountant, expense_id, {"category_id": shop.category("Autre")}, 1
        )
    with pytest.raises(ValueError, match="non modifiables"):
        shop.uc.correct.execute(shop.accountant, expense_id, {"number": "D-9"}, 1)
    same = shop.uc.correct.execute(shop.accountant, expense_id, {"amount": 25_000}, 1)
    assert same.expense.version == 1  # rien ne change : rien n'est écrit
    retagged = shop.uc.correct.execute(
        shop.accountant, expense_id, {"tag_names": ("Fête",), "beneficiary": "Ali"}, 1
    )
    assert [t.name for t in retagged.tags] == ["Fête"]
    assert retagged.expense.details.beneficiary == "Ali"


def test_cancel_requires_reason_and_leaves_totals() -> None:
    shop = shop_at_d()
    fuel = shop.record(shop.accountant, 25_000, "Carburant").expense
    shop.world.clock.move_to(datetime(2026, 11, 10, 14, 30, tzinfo=UTC))
    meal = shop.record(shop.accountant, 10_000, "Repas").expense
    shop.world.clock.move_to(datetime(2026, 11, 10, 15, 0, tzinfo=UTC))  # 16:00 à Douala
    with pytest.raises(ReasonRequired):
        shop.uc.cancel.execute(shop.accountant, meal.id, "  ")
    cancelled = shop.uc.cancel.execute(shop.accountant, meal.id, "Saisie en double")
    assert cancelled.expense.status is ExpenseStatus.CANCELLED
    assert not cancelled.editable
    listing = shop.day(D)
    assert [v.expense.number for v in listing.items] == [meal.number, fuel.number]  # visible
    assert (listing.totals.amount, listing.totals.count) == (25_000, 1)  # E2 exclue
    assert [t.category_id for t in listing.totals.by_category] == [fuel.details.category_id]
    entries = shop.world.journal(shop.world.shop_of(shop.owner))
    [cancel] = [e for e in entries if e.action is AuditAction.CANCEL]
    assert cancel.sensitive
    assert cancel.reason == "Saisie en double"
    assert cancel.entity.number == str(meal.number)


def test_inactive_references_block_new_choices_only() -> None:
    shop = shop_at_d()
    world, owner = shop.world, shop.owner
    om = shop.mode("Orange Money")
    garoua = world.location_id(world.shop_of(owner), "Garoua-Boulaï")
    view = shop.record(shop.accountant, payment_mode_id=om, location_id=garoua)
    world.http.payment_modes.update(owner, om, {"active": False}, 1)
    world.http.locations.update(owner, garoua, {"active": False}, 1)
    kept = shop.uc.correct.execute(shop.accountant, view.expense.id, {"amount": 2}, 1)
    assert kept.expense.details.payment_mode_id == om  # inchangés : acceptés
    with pytest.raises(InactiveReference):
        shop.record(shop.accountant, payment_mode_id=om)
    with pytest.raises(InactiveReference):
        shop.record(shop.accountant, location_id=garoua)
    with pytest.raises(ValidationFailed):
        shop.record(shop.accountant, tag_names=tuple(f"t{n}" for n in range(11)))
