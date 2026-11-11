"""UC-VEN-05 (SAL-09 à 11), UC-VEN-06 (RPT-01/02), UC-VEN-04 (RCP-01 à 03), UC-VEN-11
(CUS-01 à 03) et classement « plus vendus » du catalogue."""

import pytest

from app.application.catalog.ranking import ArticleOrder
from app.application.catalog.search import ArticlePageRequest, ArticleQuery
from app.application.ports.pagination import PageRequest
from app.application.sales.receipt import Mention
from app.application.sales.search import SaleCriteria
from app.application.sales.use_cases.cancel_sale import CancelSaleCommand
from app.application.sales.use_cases.error_reports import AnswerCommand, ReportCommand
from app.application.security.errors import PermissionDenied
from app.bootstrap.catalog import build_catalog
from app.bootstrap.sales import sales_ranking
from app.domain.alerts.alert import AlertType
from app.domain.sales.error_report import ReportStatus
from app.domain.shared.errors import Duplicate, NotFound
from app.domain.shared.money import Money
from app.domain.shared.roles import Role
from tests.application.sales.test_record_sale import bought


def test_own_scope_listing_search_and_rights() -> None:
    world, owner, accountant, seller, hj = bought()
    other = world.member(owner, "677000005", Role.SELLER, "Garoua")
    mine = world.cash(seller, hj, 780_000, "LBX123")
    theirs = world.cash(other, hj, 760_000)
    listing = world.sales.list.execute(seller, SaleCriteria(), PageRequest())
    assert [v.sale.id for v in listing.items] == [mine.sale.id]  # SAL-10
    assert listing.totals.total == Money(780_000)
    everyone = world.sales.list.execute(owner, SaleCriteria(), PageRequest())
    assert everyone.totals.count == 2
    assert everyone.items[0].show_costs
    with pytest.raises(NotFound):
        world.sales.get.execute(seller, theirs.sale.id)
    found = world.sales.list.execute(owner, SaleCriteria(text="lbx-123"), PageRequest())
    assert [v.sale.id for v in found.items] == [mine.sale.id]  # SAL-11, RG-M02
    by_number = world.sales.list.execute(seller, SaleCriteria(text="v-000002"), PageRequest())
    assert by_number.items == []  # vente d'un autre vendeur
    with pytest.raises(PermissionDenied):  # RG-D03
        world.sales.list.execute(accountant, SaleCriteria(), PageRequest())


def test_error_report_alert_and_reply() -> None:
    world, owner, _, seller, hj = bought()
    other = world.member(owner, "677000005", Role.SELLER, "Garoua")
    sale = world.cash(seller, hj, 780_000).sale
    with pytest.raises(NotFound):  # RPT-01 : vente d'un autre vendeur
        world.sales.report.execute(other, ReportCommand(sale_id=sale.id, description="x"))
    report, created = world.sales.report.execute(
        seller, ReportCommand(sale_id=sale.id, description="mauvais prix, c'était 750 000")
    )
    assert created
    alerts = world.alerts(owner, owner)
    assert [a.type for a in alerts] == [AlertType.SALE_ERROR_REPORTED]
    with pytest.raises(PermissionDenied):
        world.sales.answer.execute(seller, AnswerCommand(report_id=report.id, reply="ok"))
    answered = world.sales.answer.execute(
        owner, AnswerCommand(report_id=report.id, reply="Prix corrigé", version=1)
    )
    assert answered.status is ReportStatus.HANDLED
    seen = world.sales.get.execute(seller, sale.id)
    assert [r.owner_reply for r in seen.reports] == ["Prix corrigé"]  # RPT-02


def test_receipt_duplicate_and_cancelled_mentions() -> None:
    world, owner, _, seller, hj = bought()
    sale = world.credit(seller, hj, 780_000, 300_000, "LBX9").sale
    first = world.sales.receipt.execute(seller, sale.id)
    assert first.mentions == (Mention.CREDIT_SALE,)
    assert (first.seller_name, first.payments[0].mode_name) == ("Paul", "Espèces")
    assert first.lines[0].details[0].chassis_number == "LBX9"  # RG-M03
    second = world.sales.receipt.execute(owner, sale.id)
    assert second.mentions == (Mention.CREDIT_SALE, Mention.DUPLICATE)  # RCP-03
    world.sales.cancel.execute(owner, CancelSaleCommand(sale_id=sale.id, reason="x"))
    third = world.sales.receipt.execute(owner, sale.id)
    assert Mention.CANCELLED in third.mentions
    assert third.print_sequence == 3


def test_best_selling_ranking() -> None:
    world, owner, _, seller, hj = bought()
    other = world.moto(owner, model="KTM", base_price=900_000)
    world.stock_in(owner, other, "Garoua", 5)
    world.record(seller, world.line(other, 900_000, 2))
    world.cash(seller, hj, 780_000)
    catalog = build_catalog(world.identity, ranking=sales_ranking(world.clock)).http
    page = catalog.search.execute(
        owner, ArticleQuery(), ArticlePageRequest(1), ArticleOrder.BEST_SELLING
    ).page
    assert [a.id for a in page.items] == [other.id]
    assert page.next_cursor is not None
    rest = catalog.search.execute(
        owner, ArticleQuery(), ArticlePageRequest(5, page.next_cursor), ArticleOrder.BEST_SELLING
    ).page
    assert [a.id for a in rest.items] == [hj.id]


def test_customers_scope_duplicates_and_sheet() -> None:
    world, owner, accountant, seller, hj = bought()
    other = world.member(owner, "677000005", Role.SELLER, "Garoua")
    sale = world.credit(seller, hj, 780_000, 300_000).sale
    assert sale.content.customer_id is not None
    awa, created = world.sales.customers.create(other, {"name": "Awa", "phone": "677112233"})
    assert created
    assert [c.name for c in world.sales.customers.search(seller)] == ["Moussa A."]  # CUS-03
    assert [c.name for c in world.sales.customers.search(owner, "690 00")] == ["Moussa A."]
    with pytest.raises(NotFound):
        world.sales.customers.sheet(seller, awa.id)
    with pytest.raises(Duplicate) as taken:  # ERR-DUP-04
        world.sales.customers.create(seller, {"name": "X", "phone": "677 11 22 33"})
    assert "existing_id" not in taken.value.details  # client d'un autre vendeur
    sheet = world.sales.customers.sheet(owner, sale.content.customer_id)
    assert (sheet.total_bought, sheet.total_due) == (Money(780_000), Money(480_000))
    with pytest.raises(PermissionDenied):
        world.sales.customers.search(accountant)
