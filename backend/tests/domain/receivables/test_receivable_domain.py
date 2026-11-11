"""Domaine des créances : invariants, transitions § 7.1, rappels, ancienneté (Q-19), relevé."""

from datetime import date

import pytest

from app.application.receivables.statement_lines import statement_lines
from app.domain.receivables.follow_up import Reminder, ReminderStatus
from app.domain.receivables.ids import ReceivableId, ReminderId, receivable_id_for_sale
from app.domain.receivables.installment import InstallmentNature
from app.domain.receivables.receivable import Receivable
from app.domain.receivables.values import (
    ReceivableOrigin,
    ReceivableStatus,
    SeniorityBand,
    seniority_band,
)
from app.domain.sales.ids import CustomerId, SaleId
from app.domain.shared.errors import (
    InvalidAmount,
    InvalidStateTransition,
    NotFound,
    ValidationFailed,
)
from app.domain.shared.ids import ShopId
from app.domain.shared.money import Money
from tests.contracts.catalog_data import NOW
from tests.contracts.receivables_data import installment, receivable
from tests.contracts.sales_data import SELLER
from tests.contracts.test_receivables_contract import from_sale


def test_bands_q19() -> None:
    assert [seniority_band(d) for d in (0, 30, 31, 60, 61, 90, 91)] == [
        SeniorityBand.UNDER_30,
        SeniorityBand.UNDER_30,
        SeniorityBand.FROM_31_TO_60,
        SeniorityBand.FROM_31_TO_60,
        SeniorityBand.FROM_61_TO_90,
        SeniorityBand.FROM_61_TO_90,
        SeniorityBand.OVER_90,
    ]


def test_invariants() -> None:
    shop = ShopId.new()
    with pytest.raises(ValueError, match="vente liée"):
        Receivable(
            id=ReceivableId.new(),
            shop_id=shop,
            customer_id=CustomerId.new(),
            origin=ReceivableOrigin.SALE,
            opened_on=date(2026, 11, 1),
            initial_amount=Money(1),
            recorded_at=NOW,
        )
    with pytest.raises(ValueError, match="identifiant"):
        Receivable(
            id=ReceivableId.new(),
            shop_id=shop,
            customer_id=CustomerId.new(),
            origin=ReceivableOrigin.SALE,
            opened_on=date(2026, 11, 1),
            initial_amount=Money(1),
            recorded_at=NOW,
            sale_id=SaleId.new(),
        )
    with pytest.raises(ValidationFailed):  # ancienne sans description
        Receivable(
            id=ReceivableId.new(),
            shop_id=shop,
            customer_id=CustomerId.new(),
            origin=ReceivableOrigin.LEGACY,
            opened_on=date(2026, 11, 1),
            initial_amount=Money(1),
            recorded_at=NOW,
        )
    with pytest.raises(InvalidAmount):
        Receivable.open_legacy(
            shop,
            receivable_id=ReceivableId.new(),
            customer_id=CustomerId.new(),
            amount=Money(0),
            opened_on=date(2026, 1, 1),
            description="x",
            responsible_seller_id=None,
            terms=None,
            performer=SELLER,
            now=NOW,
        )
    r = receivable(shop)
    with pytest.raises(ValueError, match="nature"):
        r.record_installment(installment(1, nature=InstallmentNature.RECOVERY), performer=SELLER)
    r.record_installment(installment(1), performer=SELLER)
    with pytest.raises(ValueError, match="déjà utilisé"):
        r.record_installment(installment(1), performer=SELLER)
    with pytest.raises(NotFound):
        r.reminder(ReminderId.new())
    with pytest.raises(ValueError, match="vente"):
        r.reduce_by_return(Money(1))
    assert r.seniority(date(2026, 8, 1)) == 0


def test_sale_link_transitions() -> None:
    sale_id = SaleId.new()
    r = from_sale(ShopId.new(), sale_id)
    assert r.id == receivable_id_for_sale(sale_id)
    with pytest.raises(InvalidAmount):
        r.reduce_by_return(Money(0))
    with pytest.raises(ValueError, match="incohérent"):
        r.revise_from_sale(
            customer_id=r.customer_id, total=Money(10), paid_at_sale=Money(1), initial=Money(1)
        )
    r.record_installment(installment(1, 100_000), performer=SELLER)
    assert r.reduce_by_return(Money(400_000)) == Money(380_000)  # plafonnée au reste
    assert r.remaining == Money(0)  # Soldée
    r.cancel_by_sale(refund_payments=False, on=date(2026, 11, 12), at=NOW)
    assert r.status is ReceivableStatus.CANCELLED
    assert not r.installments[0].to_refund
    with pytest.raises(InvalidStateTransition):
        r.cancel_by_sale(refund_payments=True, on=date(2026, 11, 12), at=NOW)
    lines = statement_lines([r])
    assert [x.kind for x in lines][-1] == "cancellation"
    assert lines[-1].balance_after == Money(0)


def test_reminder_transitions() -> None:
    base = Reminder(
        id=ReminderId.new(), remind_on=date(2026, 12, 1), created_by=SELLER.user_id, created_at=NOW
    )
    assert not base.is_due(date(2026, 11, 30))
    assert base.is_due(date(2026, 12, 2))
    assert not base.alerted().is_due(date(2026, 12, 2))
    noted = base.changed(status=None, remind_on=None, note="promis")
    assert (noted.status, noted.note) == (ReminderStatus.UPCOMING, "promis")
    same = base.changed(status=ReminderStatus.UPCOMING, remind_on=None, note=None)
    assert same.status is ReminderStatus.UPCOMING
    later = base.changed(status=ReminderStatus.POSTPONED, remind_on=date(2026, 12, 9), note=None)
    with pytest.raises(InvalidStateTransition):
        later.changed(status=ReminderStatus.UPCOMING, remind_on=None, note=None)
    done = later.changed(status=ReminderStatus.DONE, remind_on=None, note=None)
    assert not done.is_due(date(2027, 1, 1))


def test_write_off_statement_and_recovery() -> None:
    r = receivable(ShopId.new(), opened_on=date(2026, 11, 1))
    r.record_installment(installment(1), performer=SELLER)
    r.mark_written_off("parti", on=date(2026, 11, 11), performer=SELLER, now=NOW)
    later = installment(2, 10_000, InstallmentNature.RECOVERY)
    r.record_installment(later, performer=SELLER)
    assert r.status is ReceivableStatus.WRITTEN_OFF
    kinds = [(x.kind, x.balance_after.amount) for x in statement_lines([r])]
    assert kinds[0] == ("opening", 300_000)
    assert kinds[-1][1] == 0  # sortie du dû : la récupération n'y change rien
