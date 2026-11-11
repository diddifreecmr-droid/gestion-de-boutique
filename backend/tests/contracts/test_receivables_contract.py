"""Contrat du module Créances (T17) : aller-retour avec enfants, unicités (une créance par vente,
numéro de versement), isolation, portée « Siennes », recherches par versement et rappel,
rappels dus.

Rejoué sur l'adaptateur mémoire, sur SQLite (`tests/infrastructure/sqlalchemy`) et sur
PostgreSQL (`--backend=postgres`).
"""

from datetime import date

import pytest

from app.application.receivables.ports import ReceivableRepository
from app.domain.receivables.ids import InstallmentId, ReminderId
from app.domain.receivables.receivable import Receivable
from app.domain.sales.ids import CustomerId, SaleId
from app.domain.sales.receivable_events import CreditSaleRecorded
from app.domain.shared.errors import Duplicate, NotFound
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money
from tests.contracts.backends import ContractBackend
from tests.contracts.catalog_data import NOW
from tests.contracts.helpers import run_in_uow
from tests.contracts.receivables_data import furnished, installment, receivable, same
from tests.contracts.sales_data import SELLER


def add(backend: ContractBackend, shop: ShopId, *items: Receivable) -> None:
    def action(uow) -> None:  # type: ignore[no-untyped-def]
        for item in items:
            ReceivableRepository.within(uow).add(item)

    run_in_uow(backend, shop, action)


def from_sale(shop: ShopId, sale_id: SaleId) -> Receivable:
    event = CreditSaleRecorded(
        shop_id=shop,
        occurred_at=NOW,
        sale_id=sale_id,
        sale_number="V-000001",
        customer_id=CustomerId.new(),
        responsible_seller_id=SELLER.user_id,
        initial_amount=Money(480_000),
        opened_on=date(2026, 11, 11),
        reminder_on=date(2026, 12, 1),
        terms="100 000 / mois",
    )
    return Receivable.open_from_sale(event, total=Money(780_000))


def test_round_trip_update_and_isolation(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    full = furnished(shop_a)
    add(backend, shop_a, full)
    with backend.uow(shop_a) as uow:
        stored = ReceivableRepository.within(uow).get(full.id)
        assert same(stored, full)
        assert stored.remaining == Money(280_000)
        stored.record_installment(
            installment(3, 30_000, stored.nature_for_next()), performer=SELLER
        )
        ReceivableRepository.within(uow).update(stored)
        uow.commit()
    with backend.uow(shop_a) as uow:
        again = ReceivableRepository.within(uow).get(full.id)
    assert same(again, stored)
    assert again.version == 2
    with backend.uow(shop_b) as uow, pytest.raises(NotFound):
        ReceivableRepository.within(uow).get(full.id)
    with backend.uow(shop_b) as uow:
        assert (
            ReceivableRepository.within(uow).find_by_installment(again.installments[0].id) is None
        )


def test_sale_receivable_unique_and_installment_number(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    sale_id = SaleId.new()
    opened = from_sale(shop_a, sale_id)
    add(backend, shop_a, opened)
    with backend.uow(shop_a) as uow:
        stored = ReceivableRepository.within(uow).get(opened.id)
    assert same(stored, opened)
    assert stored.reminders[0].remind_on == date(2026, 12, 1)
    twin = receivable(shop_a)
    twin.origin, twin.sale_id = opened.origin, sale_id  # même vente : interdit
    object.__setattr__(twin, "id", opened.id.__class__.new())
    with pytest.raises(Duplicate) as clash:
        add(backend, shop_a, twin)
    assert clash.value.details["constraint"] in ("receivable_sale",)
    first, second = receivable(shop_a), receivable(shop_a)
    first.record_installment(installment(7), performer=SELLER)
    second.record_installment(installment(7), performer=SELLER)
    add(backend, shop_a, first)
    with pytest.raises(Duplicate):
        add(backend, shop_a, second)


def test_queries_scope_and_due_reminders(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    customer = CustomerId.new()
    other_seller = UserId.new()
    late = receivable(shop_a, customer_id=customer, opened_on=date(2026, 10, 1))
    early = receivable(shop_a, customer_id=customer, opened_on=date(2026, 9, 1))
    theirs = receivable(shop_a, responsible=other_seller)
    full = furnished(shop_a, remind_on=date(2026, 11, 30))
    add(backend, shop_a, late, early, theirs, full)
    add(backend, shop_b, receivable(shop_b, customer_id=customer))
    with backend.uow(shop_a) as uow:
        repo = ReceivableRepository.within(uow)
        assert [r.id for r in repo.for_customer(customer)] == [early.id, late.id]
        assert [r.id for r in repo.list_all(responsible=other_seller)] == [theirs.id]
        assert len(repo.list_all()) == 4
        assert repo.for_customer(customer, responsible=other_seller) == []
        reminder_id = full.reminders[0].id
        assert repo.find_by_reminder(reminder_id).id == full.id  # type: ignore[union-attr]
        assert repo.find_by_installment(full.installments[1].id).id == full.id  # type: ignore[union-attr]
        assert repo.find_by_installment(InstallmentId.new()) is None
        assert repo.find_by_reminder(ReminderId.new()) is None
        assert repo.with_due_reminders(date(2026, 11, 29)) == []
        due = repo.with_due_reminders(date(2026, 11, 30))
        assert [r.id for r in due] == [full.id]
        due[0].mark_reminder_alerted(reminder_id, now=NOW, message="Rappel")
        repo.update(due[0])
        uow.commit()
    with backend.uow(shop_a) as uow:
        assert ReceivableRepository.within(uow).with_due_reminders(date(2026, 12, 2)) == []
