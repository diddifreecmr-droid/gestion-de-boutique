"""UC-CRE-03 / UC-CRE-08 — Versements : SCN-07 (soldée, OVERPAYMENT, annulation), REC-03
(plus ancienne créance), numérotation `R-` continue, idempotence, portée et reçu."""

from datetime import date

import pytest

from app.application.receivables.use_cases.record_installment import InstallmentCommand
from app.application.security.errors import PermissionDenied
from app.domain.purchasing.errors import ReasonRequired
from app.domain.receivables.errors import ReceivableOverpayment
from app.domain.receivables.ids import InstallmentId, receivable_id_for_sale
from app.domain.receivables.installment import InstallmentStatus
from app.domain.receivables.values import ReceivableStatus
from app.domain.shared.errors import DateOutOfRange, NotFound, ValidationFailed
from app.domain.shared.money import Money
from app.domain.shared.roles import Role
from tests.application.receivables.support import ReceivablesWorld


def test_scn07_installments_settle_then_cancel_reopens() -> None:
    world = ReceivablesWorld()
    owner, _, seller, _, view = world.scn01()
    rid = view.receivable.id
    first = world.versement(seller, rid, 200_000, "Orange Money")
    assert (str(first.installment.number), first.view.receivable.remaining) == (
        "R-000001",
        Money(280_000),
    )
    receipt = world.receivables.receipt.execute(seller, first.installment.id)
    assert (receipt.total_paid, receipt.remaining, receipt.settled) == (
        Money(500_000),
        Money(280_000),
        False,
    )
    assert (receipt.customer_name, receipt.mode_name) == ("Moussa A.", "Orange Money")
    with pytest.raises(ReceivableOverpayment) as refused:
        world.versement(seller, rid, 300_000)
    assert refused.value.details["remaining"] == 280_000
    second = world.versement(seller, rid, 280_000)
    assert str(second.installment.number) == "R-000002"  # aucun numéro consommé par le refus
    assert second.view.receivable.status is ReceivableStatus.SETTLED
    assert world.receivables.receipt.execute(owner, second.installment.id).settled
    with pytest.raises(ReceivableOverpayment):
        world.versement(seller, rid, 1)
    with pytest.raises(PermissionDenied):
        world.receivables.cancel_installment.execute(seller, second.installment.id, "erreur")
    with pytest.raises(ReasonRequired):
        world.receivables.cancel_installment.execute(owner, second.installment.id, " ")
    done = world.receivables.cancel_installment.execute(
        owner, second.installment.id, "chèque sans provision"
    )
    assert done.installment.status is InstallmentStatus.CANCELLED
    assert (done.view.receivable.status, done.view.receivable.remaining) == (
        ReceivableStatus.OPEN,
        Money(280_000),
    )
    cancelled = world.receivables.receipt.execute(owner, second.installment.id)
    assert (cancelled.settled, cancelled.remaining) == (False, Money(280_000))
    third = world.versement(owner, rid, 10_000)
    assert str(third.installment.number) == "R-000003"  # numérotation continue


def test_rec03_default_to_oldest_receivable_and_explicit_choice() -> None:
    world = ReceivablesWorld()
    _, _, seller, hj, view = world.scn01()
    world.at(date(2026, 11, 12))
    newer = world.credit(seller, hj, 780_000, 300_000).sale
    customer_id = view.receivable.customer_id
    paid = world.versement(seller, None, 50_000, customer_id=customer_id)
    assert paid.view.receivable.id == view.receivable.id  # la plus ancienne
    chosen = world.versement(seller, paid.view.receivable.id, 1_000)
    assert chosen.view.receivable.id == view.receivable.id

    explicit = world.versement(seller, receivable_id_for_sale(newer.id), 2_000)
    assert explicit.view.receivable.sale_number == "V-000002"
    with pytest.raises(ValidationFailed):  # ni créance ni client
        world.receivables.record_installment.execute(
            seller, InstallmentCommand(amount=1, mode_id=world.mode(seller))
        )


def test_idempotent_replay_date_window_and_scope() -> None:
    world = ReceivablesWorld()
    owner, accountant, seller, _, view = world.scn01()
    rid = view.receivable.id
    command = InstallmentCommand(
        amount=10_000,
        mode_id=world.mode(seller),
        receivable_id=rid,
        installment_id=InstallmentId.new(),
    )
    first, created = world.receivables.record_installment.execute(seller, command)
    again, replayed = world.receivables.record_installment.execute(seller, command)
    assert (created, replayed) == (True, False)
    assert again.installment.number == first.installment.number
    old = InstallmentCommand(
        amount=1, mode_id=world.mode(seller), receivable_id=rid, paid_on=date(2026, 11, 1)
    )
    with pytest.raises(DateOutOfRange):  # vendeur : J-7 au plus (RG-T09)
        world.receivables.record_installment.execute(seller, old)
    other = world.member(owner, "677000009", Role.SELLER, "Garoua")
    with pytest.raises(NotFound):  # M19 : créance d'un autre vendeur → 404
        world.versement(other, rid, 1_000)
    with pytest.raises(NotFound):
        world.get(other, rid)
    with pytest.raises(PermissionDenied):  # comptable : 403 (RG-D03)
        world.versement(accountant, rid, 1_000)
    with pytest.raises(PermissionDenied):
        world.get(accountant, rid)
