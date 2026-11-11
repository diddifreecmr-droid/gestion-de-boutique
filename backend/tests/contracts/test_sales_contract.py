"""Contrat du module Ventes (T16a) : aller-retour avec enfants, unicités (numéro, téléphone,
châssis actif, rang d'impression), isolation, lectures par période, annulation, référence,
client, quantités vendues et portée « ses clients ».

Rejoué sur l'adaptateur mémoire, sur SQLite (`tests/infrastructure/sqlalchemy`) et sur
PostgreSQL (`--backend=postgres`).
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.application.sales.ports import (
    ChassisClaimRepository,
    CustomerQuery,
    CustomerRepository,
    ErrorReportRepository,
    ReceiptPrintRepository,
    SaleRepository,
)
from app.domain.identity.phone import PhoneNumber
from app.domain.sales.chassis import ChassisClaim
from app.domain.sales.error_report import ErrorReport
from app.domain.sales.receipt_print import ReceiptPrint
from app.domain.shared.errors import Duplicate, NotFound
from app.domain.shared.ids import ShopId, UserId
from tests.contracts.backends import ContractBackend
from tests.contracts.catalog_data import NOW
from tests.contracts.helpers import run_in_uow
from tests.contracts.sales_data import ARTICLE, SELLER, customer, sale, same


def test_sale_round_trip_cancel_and_isolation(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    buyer = customer(shop_a)
    sold = sale(shop_a, 1, customer_id=buyer.id)

    def add(uow) -> None:  # type: ignore[no-untyped-def]
        CustomerRepository.within(uow).add(buyer)
        SaleRepository.within(uow).add(sold)

    run_in_uow(backend, shop_a, add)
    with backend.uow(shop_a) as uow:
        stored = SaleRepository.within(uow).get(sold.id)
        assert same(stored, sold)
        assert stored.content.lines[0].margin is not None
        stored.cancel("doublon", refund_payments=False, performer=SELLER, now=NOW)
        SaleRepository.within(uow).update(stored)
        uow.commit()
    with backend.uow(shop_a) as uow:
        again = SaleRepository.within(uow).get(sold.id)
        found = CustomerRepository.within(uow).get(buyer.id)
    assert same(again, stored)
    assert again.version == 2
    assert found.details == buyer.details
    assert found.created_by == SELLER.user_id
    with backend.uow(shop_b) as uow, pytest.raises(NotFound):
        SaleRepository.within(uow).get(sold.id)
    with pytest.raises(Duplicate) as twin:
        run_in_uow(backend, shop_a, lambda uow: SaleRepository.within(uow).add(sale(shop_a, 1)))
    assert twin.value.details["constraint"] == "sale_number"
    clash = customer(shop_a, "+237 690 00 00 00", "Autre")
    with pytest.raises(Duplicate) as phone:
        run_in_uow(backend, shop_a, lambda uow: CustomerRepository.within(uow).add(clash))
    assert phone.value.details["constraint"] == "customer_phone"
    run_in_uow(backend, shop_b, lambda uow: CustomerRepository.within(uow).add(customer(shop_b)))


def test_sale_readings(backend: ContractBackend, shop_a: ShopId) -> None:
    other = UserId.new()
    buyer = customer(shop_a)
    old = sale(shop_a, 1, on=date(2026, 11, 9), chassis="AAA1")
    mine = sale(shop_a, 2, customer_id=buyer.id, quantity=3)
    theirs = sale(shop_a, 3, seller=other, chassis=None)

    def add(uow) -> None:  # type: ignore[no-untyped-def]
        CustomerRepository.within(uow).add(buyer)
        for item in (old, mine, theirs):
            SaleRepository.within(uow).add(item)

    run_in_uow(backend, shop_a, add)
    with backend.uow(shop_a) as uow:
        sales = SaleRepository.within(uow)
        today = date(2026, 11, 11)
        assert [str(s.number) for s in sales.list_between(today, today)] == [
            "V-000003",
            "V-000002",
        ]
        assert [s.id for s in sales.list_between(today, today, seller=other)] == [theirs.id]
        assert [s.id for s in sales.find_by_reference(None, "LBX123")] == [mine.id]
        provisional = str(old.provisional_number)
        assert [s.id for s in sales.find_by_reference(provisional, None)] == [old.id]
        assert [s.id for s in sales.for_customer(buyer.id)] == [mine.id]
        assert sales.for_customer(buyer.id, seller=other) == []
        sold = sales.quantities_since(NOW - timedelta(days=1))
        assert sold[ARTICLE] == Decimal(4)  # 1 (theirs) + 3 (mine) ; `old` hors fenêtre
        stale = sales.get(mine.id)
        stale.cancel("x", refund_payments=False, performer=SELLER, now=NOW)
        sales.update(stale)
        uow.commit()
    with backend.uow(shop_a) as uow:
        sales = SaleRepository.within(uow)
        cancelled = sales.cancelled_between(date(2026, 11, 11), date(2026, 11, 11))
        assert [s.id for s in cancelled] == [mine.id]
        assert sales.quantities_since(NOW - timedelta(days=1))[ARTICLE] == Decimal(1)
        customers = CustomerRepository.within(uow)
        assert customers.visible_to(buyer.id, SELLER.user_id)
        assert not customers.visible_to(buyer.id, other)
        assert [c.id for c in customers.search(CustomerQuery("690 00"))] == [buyer.id]
        assert customers.search(CustomerQuery("mou", seller=other)) == []
        assert customers.find_by_phone(PhoneNumber.parse("690000000")) is not None


def test_chassis_claims_reports_and_prints(backend: ContractBackend, shop_a: ShopId) -> None:
    sold = sale(shop_a, 1)
    claim = ChassisClaim.claim(shop_a, "LBX 123", sold.id, "V-000001")
    run_in_uow(backend, shop_a, lambda uow: ChassisClaimRepository.within(uow).add(claim))
    rival = ChassisClaim.claim(shop_a, "lbx123", sold.id, "V-000002")
    with pytest.raises(Duplicate) as taken:
        run_in_uow(backend, shop_a, lambda uow: ChassisClaimRepository.within(uow).add(rival))
    assert taken.value.details["constraint"] == "sold_chassis_active"
    with backend.uow(shop_a) as uow:
        claims = ChassisClaimRepository.within(uow)
        held = claims.find_active("LBX123")
        assert held is not None
        assert held.sale_number == "V-000001"
        held.release()
        claims.update(held)
        uow.commit()
    run_in_uow(backend, shop_a, lambda uow: ChassisClaimRepository.within(uow).add(rival))
    with backend.uow(shop_a) as uow:
        assert len(ChassisClaimRepository.within(uow).for_sale(sold.id)) == 2
    report = ErrorReport.report(shop_a, sold.id, "V-000001", "prix", performer=SELLER, now=NOW)
    run_in_uow(backend, shop_a, lambda uow: ErrorReportRepository.within(uow).add(report))
    with backend.uow(shop_a) as uow:
        stored = ErrorReportRepository.within(uow).for_sale(sold.id)[0]
        stored.answer("vu", handled=True, performer=SELLER, now=NOW)
        ErrorReportRepository.within(uow).update(stored)
        uow.commit()
    with backend.uow(shop_a) as uow:
        assert ErrorReportRepository.within(uow).get(report.id).owner_reply == "vu"

    def printed(sequence: int) -> ReceiptPrint:
        return ReceiptPrint.record(shop_a, sold.entity, sequence, performer=SELLER, now=NOW)

    run_in_uow(backend, shop_a, lambda uow: ReceiptPrintRepository.within(uow).add(printed(1)))
    with pytest.raises(Duplicate) as again:
        run_in_uow(backend, shop_a, lambda uow: ReceiptPrintRepository.within(uow).add(printed(1)))
    assert again.value.details["constraint"] == "receipt_print_sequence"
    with backend.uow(shop_a) as uow:
        assert ReceiptPrintRepository.within(uow).count_for(sold.id) == 1
