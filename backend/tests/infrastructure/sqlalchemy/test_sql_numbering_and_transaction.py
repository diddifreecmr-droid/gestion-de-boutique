"""Numérotation SQL (création concurrente du compteur) et transaction SQL (cycle de vie)."""

import pytest
import sqlalchemy as sa

from app.application.ports.errors import UnitOfWorkStateError
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.ids import ShopId
from app.infrastructure.persistence.sqlalchemy.numbering import SqlDocumentNumberAllocator
from app.infrastructure.persistence.sqlalchemy.tables import document_counter
from app.infrastructure.persistence.sqlalchemy.transaction import SqlTransaction
from app.infrastructure.persistence.sqlalchemy.uow import SqlUnitOfWork, SqlUnitOfWorkFactory
from tests.contracts.backends.sql import SQL_REGISTRY, SqlContractBackend
from tests.contracts.handlers import RecordingHandler
from tests.contracts.widget import Widget, WidgetRepository

SHOP = ShopId.new()


def seed_counter(engine: sa.Engine, last_value: int) -> None:
    with engine.begin() as connection:
        connection.execute(
            sa.insert(document_counter).values(
                shop_id=SHOP.value, doc_type="V", last_value=last_value, version=1
            )
        )


def test_counter_created_concurrently_is_incremented(
    backend: SqlContractBackend, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_counter(backend.engine, 4)  # « l'autre transaction » a créé le compteur
    transaction = SqlTransaction(backend.engine)
    allocator = SqlDocumentNumberAllocator(transaction, SHOP)
    real_increment = allocator._increment
    calls: list[bool] = []

    def first_misses(doc_type: DocType) -> bool:
        calls.append(True)
        return False if len(calls) == 1 else real_increment(doc_type)  # ligne pas encore vue

    monkeypatch.setattr(allocator, "_increment", first_misses)
    assert allocator.next(DocType.SALE) == DocNumber(DocType.SALE, 5)  # INSERT refusé → reprise
    transaction.discard()


def test_counter_neither_incrementable_nor_creatable_fails_loudly(
    backend: SqlContractBackend, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_counter(backend.engine, 1)
    transaction = SqlTransaction(backend.engine)
    allocator = SqlDocumentNumberAllocator(transaction, SHOP)
    monkeypatch.setattr(allocator, "_increment", lambda doc_type: False)
    with pytest.raises(RuntimeError, match="ni incrémentable ni créable"):
        allocator.next(DocType.SALE)
    transaction.discard()


def test_counter_vanishing_after_increment_fails_loudly(
    backend: SqlContractBackend, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_counter(backend.engine, 1)
    transaction = SqlTransaction(backend.engine)
    allocator = SqlDocumentNumberAllocator(transaction, SHOP)
    monkeypatch.setattr(transaction, "fetch_one", lambda statement: None)
    with pytest.raises(RuntimeError, match="disparu"):
        allocator.next(DocType.SALE)
    transaction.discard()


def test_transaction_is_closed_after_commit(backend: SqlContractBackend) -> None:
    transaction = SqlTransaction(backend.engine)
    transaction.commit()
    transaction.discard()  # sans effet : déjà validée, connexion déjà rendue
    with pytest.raises(UnitOfWorkStateError, match="déjà validée"):
        transaction.exists(sa.select(document_counter))


def test_failed_begin_returns_the_connection(
    backend: SqlContractBackend, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_begin(self: sa.Connection) -> sa.RootTransaction:
        raise sa.exc.OperationalError("BEGIN", {}, Exception("panne simulée"))

    monkeypatch.setattr(sa.Connection, "begin", broken_begin)
    with pytest.raises(sa.exc.OperationalError, match="panne simulée"):
        SqlTransaction(backend.engine)


def test_adapter_hooks_refuse_use_before_begin(backend: SqlContractBackend) -> None:
    uow = SqlUnitOfWork(backend.engine, SHOP, repositories=SQL_REGISTRY)
    with pytest.raises(UnitOfWorkStateError, match="non ouverte"):
        uow._numbering()  # primitive appelée hors cycle : garde-fou testé
    with pytest.raises(UnitOfWorkStateError, match="non ouverte"):
        uow._has_pending_changes()


def test_factory_builds_uows_sharing_one_engine(backend: SqlContractBackend) -> None:
    recorder = RecordingHandler()
    factory = SqlUnitOfWorkFactory(backend.engine, SQL_REGISTRY, [recorder])
    widget = Widget.create(SHOP, "partagé")
    with factory(SHOP) as uow:
        WidgetRepository.within(uow).add(widget)
        uow.commit()
    with factory(SHOP) as uow:
        assert WidgetRepository.within(uow).get(widget.id).label == "partagé"
    assert len(recorder.received) == 1
    assert factory.engine is backend.engine
