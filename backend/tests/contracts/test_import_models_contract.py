"""Contrat des modèles d'import (T33, T34) sur chaque adaptateur : aperçu sans écriture,
confirmation en **une** transaction (articles, Reprise de départ et coûts, clients, créances
avec client créé et rappel, fournisseurs), relecture, rejeu idempotent, journal « Importer »,
et tout ou rien quand l'écriture échoue."""

from collections.abc import Sequence

import pytest

from app.application.audit.ports import AuditLog, AuditQuery
from app.application.audit.recorder import AuditRecorder
from app.application.catalog.ports import ARTICLE_BRAND_MODEL, ArticleRepository
from app.application.imports.access import ImportAccess
from app.application.imports.kinds.articles import ArticlesImport
from app.application.imports.kinds.customers import CustomersImport
from app.application.imports.kinds.opening_stock import OpeningStockImport
from app.application.imports.kinds.receivables import ReceivablesImport
from app.application.imports.kinds.suppliers import SuppliersImport
from app.application.imports.models import ImportModel, ImportModels, ImportRun
from app.application.imports.ports import ImportBatchRepository
from app.application.imports.previews import PreviewFiles
from app.application.imports.use_cases.confirm_import import ConfirmCommand, ConfirmImport
from app.application.imports.use_cases.preview_import import PreviewCommand, PreviewImport
from app.application.ports.pagination import PageRequest
from app.application.ports.uow import UnitOfWork
from app.application.purchasing.ports import SupplierRepository
from app.application.receivables.ports import ReceivableRepository
from app.application.sales.ports import CustomerQuery, CustomerRepository
from app.application.security.actor import Actor
from app.application.security.policy import Policy
from app.application.stock.ports import StockMovementLog
from app.domain.audit.values import AuditAction
from app.domain.catalog.keys import identity_key
from app.domain.imports.batch import ImportBatch, ImportedItem
from app.domain.imports.sheet import ParsedRow
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shared.roles import Role
from app.domain.shops.ids import MerchantAccountId
from app.infrastructure.persistence.memory.clock import FixedClock
from app.infrastructure.spreadsheets.reader import TabularReader
from app.infrastructure.storage.memory import MemoryFileStorage
from tests.contracts.backends import ContractBackend
from tests.contracts.catalog_data import NOW
from tests.contracts.shop_data import seed_shop_and_settings


class Exploding(ArticlesImport):
    def apply(
        self, uow: UnitOfWork, actor: Actor, rows: Sequence[ParsedRow], run: ImportRun
    ) -> tuple[ImportedItem, ...]:
        super().apply(uow, actor, rows, run)
        msg = "panne après écriture"
        raise RuntimeError(msg)


class Bench:
    def __init__(self, backend: ContractBackend, shop: ShopId, *models: ImportModel) -> None:
        clock = FixedClock(NOW)
        self.backend, self.shop = backend, shop
        self.owner = Actor.member(
            user_id=UserId.new(), device_id=DeviceId.new(), shop_id=shop, role=Role.OWNER
        )
        registry = ImportModels(models or (
            ArticlesImport(), OpeningStockImport(clock), CustomersImport(),
            ReceivablesImport(clock, backend.platform_uow), SuppliersImport(),
        ))  # fmt: skip
        access, reader = ImportAccess(Policy(clock=clock.now), registry), TabularReader()
        previews = PreviewFiles(MemoryFileStorage())

        def uows(shop_id: ShopId) -> UnitOfWork:
            return backend.uow(shop_id, [AuditRecorder(clock)])

        self.preview = PreviewImport(uows, access, clock, reader, previews)
        self.confirm = ConfirmImport(uows, access, clock, reader, previews)

    def run(self, kind: str, content: str) -> tuple[ImportBatch, ConfirmCommand]:
        command = PreviewCommand(kind=kind, content=content.encode())
        found = self.preview.execute(self.owner, command)
        confirm = ConfirmCommand(preview_id=found.preview_id)
        batch, created = self.confirm.execute(self.owner, confirm)
        assert created
        return batch, confirm


def _seed(backend: ContractBackend, shop: ShopId) -> None:
    with backend.uow(shop) as uow:
        seed_shop_and_settings(uow, MerchantAccountId.new())
        uow.commit()


def test_every_model_writes_its_batch(backend: ContractBackend, shop_a: ShopId) -> None:
    _seed(backend, shop_a)
    bench = Bench(backend, shop_a)
    articles, replay = bench.run("articles", "Marque;Modèle\nHaojue;HJ125-8\n")
    stock, _ = bench.run(
        "opening_stock",
        "Marque;Modèle;Lieu;Quantité;Coût unitaire\n"
        "Haojue;HJ125-8;Garoua;2;450 000\nTVS;Star;Garoua;1;300 000\n",
    )
    with backend.uow(shop_a) as uow:
        repository = ArticleRepository.within(uow)
        haojue = repository.find_by_key(ARTICLE_BRAND_MODEL, identity_key("Haojue", "HJ125-8"))
        tvs = repository.find_by_key(ARTICLE_BRAND_MODEL, identity_key("TVS", "Star"))
        assert haojue is not None
        assert tvs is not None
        [entry] = StockMovementLog.within(uow).chronology(haojue.id)
        found = ImportBatchRepository.within(uow).get(stock.id)
        journal = AuditLog.within(uow).search(AuditQuery(), PageRequest(limit=50)).items
    assert (haojue.wac, haojue.last_cost, tvs.wac) == (Money(450_000), Money(450_000), Money(300_000))
    assert (entry.source.number, entry.unit_cost) == ("IMP-000002", Money(450_000))
    assert found.items == stock.items
    assert len(found.items) == 3  # deux mouvements, un article créé
    assert [e.entity.number for e in journal if e.action is AuditAction.IMPORT] == [
        "IMP-000002", "IMP-000001",
    ]  # fmt: skip
    again, created = bench.confirm.execute(bench.owner, replay)
    assert (again.id, created) == (articles.id, False)
    bench.run("customers", "Nom;Téléphone\nAli Bouba;690000001\n")
    receivables, _ = bench.run(
        "receivables",
        "Téléphone du client;Montant restant dû;Date d'origine;Nom du client;Date de rappel\n"
        "690000001;300 000;01/03/2026;;\n690000009;50 000;02/03/2026;Moussa;20/11/2026\n",
    )
    bench.run("suppliers", "Nom;Pays\nEts Haojue;Chine\n")
    with backend.uow(shop_a) as uow:
        names = sorted(c.name for c in CustomerRepository.within(uow).search(CustomerQuery()))
        debts = ReceivableRepository.within(uow).list_all()
        suppliers = [s.name for s in SupplierRepository.within(uow).list_all()]
    assert names == ["Ali Bouba", "Moussa"]
    assert sorted(d.initial_amount.amount for d in debts) == [50_000, 300_000]
    assert sum(len(d.reminders) for d in debts) == 1
    assert len(receivables.items) == 3  # deux créances, un client créé
    assert suppliers == ["Ets Haojue"]


def test_a_failed_write_leaves_nothing(backend: ContractBackend, shop_a: ShopId) -> None:
    _seed(backend, shop_a)
    bench = Bench(backend, shop_a, Exploding())
    command = PreviewCommand(kind="articles", content=b"Marque;Mod\xc3\xa8le\nHaojue;HJ125-8\n")
    found = bench.preview.execute(bench.owner, command)
    with pytest.raises(RuntimeError, match="panne"):
        bench.confirm.execute(bench.owner, ConfirmCommand(preview_id=found.preview_id))
    with backend.uow(shop_a) as uow:
        key = identity_key("Haojue", "HJ125-8")
        assert ArticleRepository.within(uow).find_by_key(ARTICLE_BRAND_MODEL, key) is None
        assert ImportBatchRepository.within(uow).find_by_preview(found.preview_id) is None
    good = Bench(backend, shop_a)
    batch, _ = good.run("articles", "Marque;Modèle\nHaojue;HJ125-8\n")
    assert str(batch.number) == "IMP-000001"  # le numéro de l'essai manqué n'est pas perdu
