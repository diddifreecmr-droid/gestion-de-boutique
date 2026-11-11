"""UC-CRE-06 (REM-01, REM-02), UC-CRE-04 (REC-04, REC-05) et UC-CRE-05 (REC-06)."""

from datetime import date, timedelta

import pytest

from app.application.receivables.use_cases.follow_up import ReminderChange
from app.application.receivables.use_cases.read_receivables import ReceivableCriteria
from app.application.receivables.use_cases.record_legacy import LegacyReceivableCommand
from app.application.sales.inputs import CustomerInput
from app.application.security.actor import Actor
from app.domain.alerts.alert import Alert, AlertType
from app.domain.receivables.follow_up import ReminderStatus
from app.domain.receivables.values import ReceivableStatus, SeniorityBand
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed
from app.domain.shared.money import Money
from tests.application.receivables.support import ReceivablesWorld


def reminder_alerts(world: ReceivablesWorld, shop_actor: Actor, recipient: Actor) -> list[Alert]:
    found = world.alerts(shop_actor, recipient)
    return [a for a in found if a.type is AlertType.RECEIVABLE_REMINDER]


def test_rem01_due_reminder_alerts_once_then_postpone() -> None:
    world = ReceivablesWorld()
    owner, accountant, seller, _, view = world.scn01()
    rid, shop = view.receivable.id, world.shop_of(owner)
    planned = world.receivables.schedule_reminder.execute(
        seller, rid, date(2026, 12, 1), "Il a promis 200 000 fin du mois"
    )
    reminder = planned.receivable.reminders[0]
    dispatch = world.receivables_module.dispatch_reminders
    assert dispatch.execute(shop, date(2026, 11, 30)) == 0
    world.at(date(2026, 12, 1), 0)
    assert dispatch.execute(shop, date(2026, 12, 1)) == 1
    assert dispatch.execute(shop, date(2026, 12, 1)) == 0  # idempotent
    assert len(reminder_alerts(world, owner, seller)) == 1
    assert len(reminder_alerts(world, owner, owner)) == 1
    assert reminder_alerts(world, owner, accountant) == []
    with pytest.raises(ValidationFailed):  # un report demande une date
        world.receivables.change_reminder.execute(
            seller, ReminderChange(reminder_id=reminder.id, status=ReminderStatus.POSTPONED)
        )
    moved = world.receivables.change_reminder.execute(
        seller, ReminderChange(reminder_id=reminder.id, remind_on=date(2026, 12, 5))
    )
    assert moved.receivable.reminders[0].status is ReminderStatus.POSTPONED
    assert dispatch.execute(shop, date(2026, 12, 5)) == 1  # réarmé pour la nouvelle date
    done = world.receivables.change_reminder.execute(
        owner, ReminderChange(reminder_id=reminder.id, status=ReminderStatus.DONE)
    )
    assert done.receivable.reminders[0].status is ReminderStatus.DONE
    with pytest.raises(InvalidStateTransition):
        world.receivables.change_reminder.execute(
            owner, ReminderChange(reminder_id=reminder.id, note="encore")
        )
    assert dispatch.execute(shop, date(2026, 12, 31)) == 0


def test_rec04_rec05_summary_sort_and_filters() -> None:
    world = ReceivablesWorld()
    owner, _, seller, _, view = world.scn01()
    today = date(2026, 11, 11)
    for days, phone in ((30, "699000030"), (31, "699000031"), (91, "699000091")):
        command = LegacyReceivableCommand(
            customer=CustomerInput(name=f"Client {days}", phone=phone),
            amount=1_000 * days,
            opened_on=today - timedelta(days=days),
            description=f"cahier {days}",
        )
        world.receivables.record_legacy.execute(owner, command)
    world.versement(seller, view.receivable.id, 80_000)
    listing = world.receivables.list.execute(owner, ReceivableCriteria())
    assert listing.summary.total_due == Money(400_000 + 30_000 + 31_000 + 91_000)
    assert listing.summary.debtor_count == 4
    assert listing.summary.received_today == Money(80_000)
    assert [v.receivable.remaining.amount for v in listing.items] == [
        400_000,
        91_000,
        31_000,
        30_000,
    ]
    bands = {v.receivable.description: v.band for v in listing.items}
    assert bands["cahier 30"] is SeniorityBand.UNDER_30  # Q-19
    assert bands["cahier 31"] is SeniorityBand.FROM_31_TO_60
    assert bands["cahier 91"] is SeniorityBand.OVER_90

    def count(**criteria: object) -> int:
        found = world.receivables.list.execute(owner, ReceivableCriteria(**criteria))  # type: ignore[arg-type]
        return len(found.items)

    assert count(band=SeniorityBand.FROM_61_TO_90) == 0
    assert count(quiet=True) == 2  # 31 et 91 jours sans versement
    assert count(seller_id=seller.user_id) == 1
    assert count(status=ReceivableStatus.SETTLED) == 0
    world.receivables.schedule_reminder.execute(owner, view.receivable.id, date(2026, 11, 5), None)
    assert count(reminder_overdue=True) == 1
    mine = world.receivables.list.execute(seller, ReceivableCriteria())
    assert [v.receivable.id for v in mine.items] == [view.receivable.id]  # portée OWN
    assert mine.summary.total_due == Money(400_000)


def test_rec06_statement_running_balance() -> None:
    world = ReceivablesWorld()
    _, _, seller, _, view = world.scn01()
    world.at(date(2026, 11, 15))
    world.versement(seller, view.receivable.id, 200_000, "Orange Money")
    world.versement(seller, view.receivable.id, 280_000)
    statement = world.receivables.statement.execute(seller, view.receivable.customer_id)
    rows = [(line.kind, line.amount.amount, line.balance_after.amount) for line in statement.lines]
    assert rows == [
        ("sale", 780_000, 780_000),
        ("deposit", 300_000, 480_000),
        ("installment", 200_000, 280_000),
        ("installment", 280_000, 0),
    ]
    assert statement.total_due == Money(0)
