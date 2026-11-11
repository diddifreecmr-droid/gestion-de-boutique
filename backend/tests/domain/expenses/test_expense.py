"""Agrégat `Expense` : montant, « Autre », délai jusqu'à minuit (Douala), annulation, brouillon."""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.domain.audit.values import Performer
from app.domain.expenses.details import Capture, ExpenseDetails
from app.domain.expenses.errors import (
    CorrectionWindowClosed,
    DescriptionRequired,
    ReasonRequired,
)
from app.domain.expenses.events import ExpenseAuditedEvent, ExpenseCancelled
from app.domain.expenses.expense import Expense, ExpenseStatus, require_description
from app.domain.expenses.ids import TagId
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.errors import InvalidAmount, InvalidStateTransition, ValidationFailed
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.shops.expense_category import ExpenseCategory
from app.domain.shops.ids import ExpenseCategoryId, PaymentModeId

SHOP = ShopId.new()
AUTHOR = Performer(UserId.new(), "accountant", DeviceId.new())
# EXP-06 : saisie le 10/11 à 15:00 heure de Douala (14:00 UTC).
SAVED = datetime(2026, 11, 10, 14, 0, tzinfo=UTC)
CATEGORY = ExpenseCategoryId.new()
MODE = PaymentModeId.new()


def details(amount: int = 25_000, **extra: object) -> ExpenseDetails:
    return ExpenseDetails(
        spent_on=date(2026, 11, 10),
        amount=amount,
        category_id=CATEGORY,
        payment_mode_id=MODE,
        **extra,  # type: ignore[arg-type]  # champs facultatifs testés
    )


def expense(at: datetime = SAVED) -> Expense:
    assert AUTHOR.device_id is not None
    capture = Capture(AUTHOR.user_id, AUTHOR.device_id, at, at)
    return Expense.record(SHOP, DocNumber(DocType.EXPENSE, 1), details(), capture, performer=AUTHOR)


@pytest.mark.parametrize("amount", [0, -1])
def test_amount_must_be_positive(amount: int) -> None:
    with pytest.raises(InvalidAmount):
        details(amount)
    with pytest.raises(TypeError):
        details(1.5)  # type: ignore[arg-type]  # flottant refusé


def test_details_are_cleaned_and_tags_deduplicated() -> None:
    tag = TagId.new()
    cleaned = details(tag_ids=(tag, tag), description="  plein   réservoir ", beneficiary=" ")
    assert cleaned.tag_ids == (tag,)
    assert cleaned.description == "plein réservoir"
    assert cleaned.beneficiary is None
    with pytest.raises(TypeError):
        details(tag_ids=("x",))
    with pytest.raises(ValidationFailed):
        details(description="x" * 501)


def test_other_category_requires_a_description() -> None:
    other = ExpenseCategory.seed_base(SHOP, "Autre", 5)
    fuel = ExpenseCategory.seed_base(SHOP, "Carburant", 1)
    assert other.requires_description
    assert not fuel.requires_description
    no_text = ExpenseDetails(
        spent_on=date(2026, 11, 10), amount=1, category_id=other.id, payment_mode_id=MODE
    )
    with pytest.raises(DescriptionRequired):
        require_description(other, no_text)
    with pytest.raises(ValueError, match="différente"):
        require_description(fuel, no_text)


def test_author_window_closes_at_midnight_douala() -> None:
    recorded = expense()
    assert recorded.correction_deadline == datetime(2026, 11, 10, 23, 0, tzinfo=UTC)
    just_before = datetime(2026, 11, 10, 22, 59, 59, tzinfo=UTC)  # 23:59:59 à Douala
    recorded.require_editable(by_owner=False, now=just_before)
    for after in (
        recorded.correction_deadline,
        recorded.correction_deadline + timedelta(minutes=1),
    ):
        with pytest.raises(CorrectionWindowClosed) as caught:
            recorded.require_editable(by_owner=False, now=after)
        assert caught.value.code == "CORRECTION_WINDOW_CLOSED"
    recorded.require_editable(by_owner=True, now=SAVED + timedelta(days=30))


def test_saved_just_before_midnight_gives_one_minute() -> None:
    late = expense(datetime(2026, 11, 10, 22, 59, tzinfo=UTC))  # 23:59 à Douala
    late.require_editable(by_owner=False, now=datetime(2026, 11, 10, 22, 59, 30, tzinfo=UTC))
    with pytest.raises(CorrectionWindowClosed):
        late.require_editable(by_owner=False, now=datetime(2026, 11, 10, 23, 1, tzinfo=UTC))


def test_correct_records_changes_and_ignores_no_op() -> None:
    recorded = expense()
    recorded.events.pull()
    assert not recorded.correct(details(), performer=AUTHOR, now=SAVED)
    assert recorded.correct(details(30_000), performer=AUTHOR, now=SAVED)
    [event] = recorded.events.pull()
    record = event.audit_record()  # type: ignore[attr-defined]  # événement journalisable
    assert [(c.field, c.before, c.after) for c in record.changes] == [("amount", 25_000, 30_000)]


def test_cancel_requires_reason_and_is_final() -> None:
    recorded = expense()
    recorded.events.pull()
    for reason in ("", "   "):
        with pytest.raises(ReasonRequired):
            recorded.cancel(reason, performer=AUTHOR, now=SAVED)
    with pytest.raises(ValidationFailed):
        recorded.cancel("x" * 501, performer=AUTHOR, now=SAVED)
    recorded.cancel(" saisie   en double ", performer=AUTHOR, now=SAVED)
    assert recorded.status is ExpenseStatus.CANCELLED
    assert recorded.cancellation is not None
    assert recorded.cancellation.reason == "saisie en double"
    [event] = recorded.events.pull()
    assert isinstance(event, ExpenseCancelled)
    audit = event.audit_record()
    assert audit.sensitive
    assert audit.reason == "saisie en double"
    with pytest.raises(InvalidStateTransition):
        recorded.cancel("encore", performer=AUTHOR, now=SAVED)
    with pytest.raises(InvalidStateTransition):
        recorded.correct(details(1), performer=AUTHOR, now=SAVED)
    with pytest.raises(InvalidStateTransition):
        recorded.require_editable(by_owner=True, now=SAVED)


def test_retag_and_repeat_draft() -> None:
    source, target, other = TagId.new(), TagId.new(), TagId.new()
    recorded = expense()
    recorded.details = details(tag_ids=(source, target), beneficiary="Paul")
    assert not recorded.retag(other, target)
    assert recorded.retag(source, target)
    assert recorded.details.tag_ids == (target,)
    draft = recorded.repeat(date(2026, 12, 10))
    assert (draft.spent_on, draft.amount, draft.tag_ids, draft.beneficiary) == (
        date(2026, 12, 10),
        25_000,
        (target,),
        "Paul",
    )


def test_record_event_and_number_type() -> None:
    recorded = expense()
    [event] = recorded.events.pull()
    record = event.audit_record()  # type: ignore[attr-defined]  # événement journalisable
    assert record.captured_at == SAVED
    assert record.entity.number == "D-000001"
    assert record.module == "expenses"
    with pytest.raises(ValueError, match="D-"):
        Expense(
            id=recorded.id,
            shop_id=SHOP,
            number=DocNumber(DocType.SALE, 1),
            details=recorded.details,
            capture=recorded.capture,
        )
    with pytest.raises(TypeError):
        ExpenseAuditedEvent(
            shop_id=SHOP, occurred_at=SAVED, performer=AUTHOR, entity=recorded.entity, summary="x"
        )
