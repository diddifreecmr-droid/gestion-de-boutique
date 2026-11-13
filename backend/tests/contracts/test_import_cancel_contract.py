"""Contrat de l'annulation des lots (T35, QC-6) sur chaque adaptateur : lignes refusées gardées,
lots listés, lot d'un élément (`batch_of`), blocage par un autre lot, contrepassation du stock
de départ, articles / clients / fournisseurs retirés **relus** tels quels et leurs clés libérées
(contraintes `article_*`, `customer_phone`, `supplier_name`), réimport accepté."""

import pytest

from app.application.audit.recorder import AuditRecorder
from app.application.catalog.ports import ARTICLE_BRAND_MODEL, ArticleRepository
from app.application.imports.ports import ImportBatchRepository, ImportProblemLog
from app.application.imports.use_cases.cancel_import import CancelImport
from app.application.ports.uow import UnitOfWork
from app.application.purchasing.ports import SupplierRepository
from app.application.sales.ports import CustomerQuery, CustomerRepository
from app.application.security.policy import Policy
from app.application.stock.ports import InventoryRepository, StockMovementLog
from app.domain.catalog.details import ArticleStatus
from app.domain.catalog.keys import identity_key
from app.domain.identity.phone import PhoneNumber
from app.domain.imports.errors import ImportCancelBlocked
from app.domain.imports.values import ImportedEntity, ImportStatus
from app.domain.sales.ids import CustomerId
from app.domain.shared.ids import ShopId
from app.domain.stock.values import MovementType
from app.infrastructure.persistence.memory.clock import FixedClock
from tests.contracts.backends import ContractBackend
from tests.contracts.catalog_data import NOW
from tests.contracts.test_import_models_contract import Bench, _seed

HAOJUE = identity_key("Haojue", "HJ125-8")
ARTICLES = "Marque;Modèle\nHaojue;HJ125-8\n;HJ200\n"
STOCK = "Marque;Modèle;Lieu;Quantité;Coût unitaire\nHaojue;HJ125-8;Garoua;2;450 000\n"


def _cancel(backend: ContractBackend, bench: Bench) -> CancelImport:
    clock = FixedClock(NOW)

    def uows(shop_id: ShopId) -> UnitOfWork:
        return backend.uow(shop_id, [AuditRecorder(clock)])

    return CancelImport(uows, Policy(clock=clock.now), clock)


def test_articles_and_opening_stock(backend: ContractBackend, shop_a: ShopId) -> None:
    _seed(backend, shop_a)
    bench = Bench(backend, shop_a)
    cancel = _cancel(backend, bench)
    articles, _ = bench.run("articles", ARTICLES)
    stock, _ = bench.run("opening_stock", STOCK)
    with backend.uow(shop_a) as uow:
        batches = ImportBatchRepository.within(uow)
        listed = [b.id for b in batches.list_all()]
        [problem] = ImportProblemLog.within(uow).for_batch(articles.id)
        article = ArticleRepository.within(uow).find_by_key(ARTICLE_BRAND_MODEL, HAOJUE)
        assert article is not None
        owner = batches.batch_of(ImportedEntity.ARTICLE, article.id.value)
        assert InventoryRepository.within(uow).started_since(NOW) == []
    assert listed == [stock.id, articles.id]
    assert (problem.line, problem.column) == (3, "Marque")
    assert owner is not None
    assert owner.id == articles.id
    with pytest.raises(ImportCancelBlocked) as blocked:
        cancel.execute(bench.owner, articles.id)
    assert blocked.value.details["blocking"] == [{"type": "import", "number": "IMP-000002"}]
    cancel.execute(bench.owner, stock.id)
    cancel.execute(bench.owner, articles.id)
    with backend.uow(shop_a) as uow:
        kept = ArticleRepository.within(uow).get(article.id)
        movements = StockMovementLog.within(uow).chronology(article.id)
        reread = ImportBatchRepository.within(uow).get(articles.id)
        assert ArticleRepository.within(uow).find_by_key(ARTICLE_BRAND_MODEL, HAOJUE) is None
    assert (kept.status, kept.keys_released, kept.wac) == (ArticleStatus.ARCHIVED, True, None)
    assert [m.type for m in movements] == [MovementType.OPENING, MovementType.REVERSAL]
    assert reread.status is ImportStatus.CANCELLED
    again, _ = bench.run("articles", ARTICLES)  # contrainte `article_brand_model` libérée
    assert again.counts.rows_imported == 1


def test_customers_and_suppliers(backend: ContractBackend, shop_a: ShopId) -> None:
    _seed(backend, shop_a)
    bench = Bench(backend, shop_a)
    cancel = _cancel(backend, bench)
    people, _ = bench.run("customers", "Nom;Téléphone\nAli Bouba;690000001\n")
    makers, _ = bench.run("suppliers", "Nom\nEts Haojue\n")
    cancel.execute(bench.owner, people.id)
    cancel.execute(bench.owner, makers.id)
    with backend.uow(shop_a) as uow:
        customers = CustomerRepository.within(uow)
        assert customers.find_by_phone(PhoneNumber.parse("690000001")) is None
        assert customers.search(CustomerQuery()) == []
        released = customers.get(CustomerId(people.items[0].entity_id))
        [supplier] = SupplierRepository.within(uow).list_all()
    assert released.released
    assert (supplier.active, supplier.released) == (False, True)
    bench.run("customers", "Nom;Téléphone\nAli Bouba;690000001\n")  # `customer_phone` libérée
    bench.run("suppliers", "Nom\nEts Haojue\n")  # `supplier_name` libérée
    with backend.uow(shop_a) as uow:
        names = [c.name for c in CustomerRepository.within(uow).search(CustomerQuery())]
        suppliers = SupplierRepository.within(uow).list_all()
    assert names == ["Ali Bouba"]
    assert sorted(s.active for s in suppliers) == [False, True]
