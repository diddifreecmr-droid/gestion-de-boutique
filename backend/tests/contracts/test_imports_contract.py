"""Contrat du dépôt `ImportBatchRepository` (mémoire, SQLite, PostgreSQL) : relecture à
l'identique avec les éléments créés, isolation des boutiques, numéro et aperçu uniques,
annulation, journal « Importer » dans la même transaction, numéros `IMP-…` continus par
boutique (NUM-01)."""

from datetime import UTC, datetime

import pytest

from app.application.audit.ports import AuditLog, AuditQuery
from app.application.audit.recorder import AuditRecorder
from app.application.imports.ports import ImportBatchRepository
from app.application.ports.pagination import PageRequest
from app.domain.audit.values import AuditAction, Performer
from app.domain.imports.batch import ImportBatch, ImportCounts, ImportedItem
from app.domain.imports.ids import ImportPreviewId
from app.domain.imports.values import ImportedEntity, ImportKind, ImportStatus
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.errors import Duplicate, NotFound
from app.domain.shared.ids import ShopId, UserId, uuid7
from app.infrastructure.persistence.memory.clock import FixedClock
from tests.contracts.backends import ContractBackend

NOW = datetime(2026, 11, 13, 9, 30, tzinfo=UTC)
OWNER = Performer(UserId.new(), "owner")
KINDS = (ImportedEntity.CUSTOMER, ImportedEntity.RECEIVABLE)


def _batch(shop: ShopId, number: DocNumber, items: int = 3) -> ImportBatch:
    created = tuple(ImportedItem(2 + n // 2, KINDS[n % 2], uuid7()) for n in range(items))
    return ImportBatch.record(
        shop, number, ImportKind.RECEIVABLES,
        preview_id=ImportPreviewId.new(), source_file_key=f"shops/{shop.value}/imports/p.bin",
        counts=ImportCounts(rows_read=items + 1, rows_imported=items, rows_ignored=1),
        items=created, performer=OWNER, now=NOW,
    )  # fmt: skip


def _record(backend: ContractBackend, shop: ShopId, items: int = 3) -> ImportBatch:
    """Numéro attribué et lot enregistré dans la même transaction, journal branché."""
    with backend.uow(shop, [AuditRecorder(FixedClock(NOW))]) as uow:
        batch = _batch(shop, uow.numbering.next(DocType.IMPORT), items)
        ImportBatchRepository.within(uow).add(batch)
        uow.commit()
    return batch


def test_round_trip_with_items_and_isolation(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    batch = _record(backend, shop_a)
    with backend.uow(shop_a) as uow:
        repository = ImportBatchRepository.within(uow)
        found = repository.get(batch.id)
        by_preview = repository.find_by_preview(batch.preview_id)
        assert repository.find_by_preview(ImportPreviewId.new()) is None
    assert by_preview is not None
    assert by_preview.id == batch.id
    assert (found.number, found.kind, found.preview_id, found.source_file_key) == (
        batch.number, batch.kind, batch.preview_id, batch.source_file_key,
    )  # fmt: skip
    assert (found.counts, found.items, found.imported_by, found.imported_at) == (
        batch.counts, batch.items, OWNER.user_id, NOW,
    )  # fmt: skip
    assert (found.status, found.cancellation, found.version) == (ImportStatus.IMPORTED, None, 1)
    with backend.uow(shop_b) as uow:
        other = ImportBatchRepository.within(uow)
        assert other.find(batch.id) is None
        assert other.find_by_preview(batch.preview_id) is None
        with pytest.raises(NotFound):
            other.get(batch.id)


def test_numbers_are_continuous_per_shop_and_kept_when_cancelled(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    first, second = _record(backend, shop_a), _record(backend, shop_a)
    neighbour = _record(backend, shop_b)
    assert [str(b.number) for b in (first, second, neighbour)] == [
        "IMP-000001", "IMP-000002", "IMP-000001",
    ]  # fmt: skip
    with backend.uow(shop_a) as uow:
        repository = ImportBatchRepository.within(uow)
        loaded = repository.get(first.id)
        loaded.cancel(performer=OWNER, now=NOW)
        repository.update(loaded)
        uow.commit()
    with backend.uow(shop_a) as uow:
        cancelled = ImportBatchRepository.within(uow).get(first.id)
    assert (str(cancelled.number), cancelled.status, cancelled.version) == (
        "IMP-000001", ImportStatus.CANCELLED, 2,
    )  # fmt: skip
    assert cancelled.cancellation is not None
    assert (cancelled.cancellation.at, cancelled.cancellation.by) == (NOW, OWNER.user_id)
    assert cancelled.items == first.items  # éléments réécrits à l'identique
    assert str(_record(backend, shop_a).number) == "IMP-000003"


def test_number_and_preview_are_unique_per_shop(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    batch = _record(backend, shop_a)
    twin_number = _batch(shop_a, batch.number)
    twin_preview = _batch(shop_a, DocNumber(DocType.IMPORT, 99))
    twin_preview.preview_id = batch.preview_id
    for twin in (twin_number, twin_preview):
        with backend.uow(shop_a) as uow:
            with pytest.raises(Duplicate):
                ImportBatchRepository.within(uow).add(twin)
            uow.rollback()
    elsewhere = _batch(shop_b, batch.number)  # même numéro, autre boutique : permis
    elsewhere.preview_id = batch.preview_id
    with backend.uow(shop_b) as uow:
        ImportBatchRepository.within(uow).add(elsewhere)
        uow.commit()


def test_import_is_journaled_in_the_same_transaction(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    batch = _record(backend, shop_a)
    with backend.uow(shop_a) as uow:
        query = AuditQuery(entity_type="import_batch", entity_id=batch.id.value)
        [entry] = AuditLog.within(uow).search(query, PageRequest()).items
    assert (entry.action, entry.module, entry.entity.number) == (
        AuditAction.IMPORT, "import", "IMP-000001",
    )  # fmt: skip


def test_a_large_batch_round_trips(backend: ContractBackend, shop_a: ShopId) -> None:
    batch = _record(backend, shop_a, items=2_500)  # plusieurs requêtes d'insertion en SQL
    with backend.uow(shop_a) as uow:
        found = ImportBatchRepository.within(uow).get(batch.id)
    assert found.items == batch.items
    assert len(found.items) == 2_500
