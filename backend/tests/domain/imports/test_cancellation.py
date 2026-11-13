"""Annulation d'un lot côté domaine (QC-6, T35) : opérations qui bloquent, erreur
`IMPORT_CANCEL_BLOCKED`, retrait des articles, clients et fournisseurs (clés libérées)."""

from datetime import UTC, datetime

import pytest

from app.application.catalog.ports import ARTICLE_NAME, held_key
from app.domain.audit.values import Performer
from app.domain.catalog.details import ArticleStatus
from app.domain.identity.phone import PhoneNumber
from app.domain.imports.blocking import BlockingOperation, BlockingType
from app.domain.imports.errors import ImportCancelBlocked
from app.domain.purchasing.supplier import Supplier, SupplierDetails
from app.domain.sales.customer import Customer, CustomerDetails
from app.domain.shared.errors import InvalidStateTransition
from app.domain.shared.ids import ShopId, UserId
from tests.domain.catalog.test_article import created

NOW = datetime(2026, 11, 13, 9, 0, tzinfo=UTC)
WHO = Performer(UserId.new(), "owner")


def test_blocking_operations_and_error_details() -> None:
    sale = BlockingOperation(BlockingType.SALE, " V-000003 ")
    other = BlockingOperation(BlockingType("import"), "IMP-000002")
    assert sale.as_detail() == {"type": "sale", "number": "V-000003"}
    error = ImportCancelBlocked(sorted({sale, other}))
    assert error.code == "IMPORT_CANCEL_BLOCKED"
    assert error.details["blocking"] == [
        {"type": "import", "number": "IMP-000002"}, {"type": "sale", "number": "V-000003"},
    ]  # fmt: skip
    with pytest.raises(ValueError, match="numéro"):
        BlockingOperation(BlockingType.SALE, "  ")
    with pytest.raises(ValueError, match="au moins"):
        ImportCancelBlocked([])


def test_a_withdrawn_article_frees_its_keys_and_stays_archived() -> None:
    article = created()
    assert held_key(article, "article_brand_model") == "haojue|hj125 8"
    article.withdraw(performer=WHO, now=NOW)
    assert (article.status, article.keys_released) == (ArticleStatus.ARCHIVED, True)
    assert held_key(article, "article_brand_model") is None
    assert held_key(article, ARTICLE_NAME) is None
    with pytest.raises(InvalidStateTransition, match="ne se réactive pas"):
        article.reactivate(performer=WHO, now=NOW)


def test_a_withdrawn_customer_frees_its_phone() -> None:
    details = CustomerDetails(name="Ali", phone=PhoneNumber.parse("690000001"))
    customer = Customer.create(ShopId.new(), details, performer=WHO, now=NOW)
    customer.events.pull()
    customer.withdraw(performer=WHO, now=NOW)
    [event] = customer.events.pull()
    assert event.audit_record().summary == "Client désactivé (import annulé) : Ali"
    assert (customer.unique_phone, customer.phone_key) == (None, "+237690000001")
    with pytest.raises(InvalidStateTransition):
        customer.withdraw(performer=WHO, now=NOW)


def test_a_withdrawn_supplier_frees_its_name_and_never_comes_back() -> None:
    supplier = Supplier.create(
        ShopId.new(), SupplierDetails(name="Ets Haojue"), performer=WHO, now=NOW
    )
    supplier.withdraw(performer=WHO, now=NOW)
    assert (supplier.active, supplier.unique_name, supplier.name_key) == (
        False, None, "ets haojue",
    )  # fmt: skip
    with pytest.raises(InvalidStateTransition, match="ne se réactive pas"):
        supplier.change(SupplierDetails(name="Ets Haojue"), performer=WHO, now=NOW)
    with pytest.raises(InvalidStateTransition):
        supplier.withdraw(performer=WHO, now=NOW)
