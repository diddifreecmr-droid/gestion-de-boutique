"""`ImportBatch` : numéro `IMP-…`, éléments tracés, journal « Importer », annulation sous 7 jours
calendaires inclus (QC-6, SCN-L3-05 étape 3 : importé le 10/11, annulable le 17/11, pas le 18)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.domain.audit.values import AuditAction, Performer
from app.domain.imports.batch import ImportBatch, ImportCounts, ImportedItem
from app.domain.imports.errors import ImportCancelTooLate
from app.domain.imports.events import ImportCancelled, ImportRecorded
from app.domain.imports.ids import ImportPreviewId
from app.domain.imports.values import ImportedEntity, ImportKind, ImportStatus
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.errors import InvalidStateTransition
from app.domain.shared.ids import ShopId, UserId, uuid7

IMPORTED = datetime(2026, 11, 10, 22, 30, tzinfo=UTC)  # 10/11 23 h 30 à Douala
OWNER = Performer(UserId.new(), "owner")


def item(line: int, entity: ImportedEntity = ImportedEntity.ARTICLE) -> ImportedItem:
    return ImportedItem(line, entity, uuid7())


def batch(**overrides: object) -> ImportBatch:
    values: dict[str, object] = {
        "preview_id": ImportPreviewId.new(),
        "source_file_key": "shops/x/imports/y.bin",
        "counts": ImportCounts(rows_read=4, rows_imported=2, rows_ignored=2),
        "items": (item(3), item(2)),
        "performer": OWNER,
        "now": IMPORTED,
    }
    values.update(overrides)
    return ImportBatch.record(
        ShopId.new(),
        DocNumber(DocType.IMPORT, 1),
        ImportKind.ARTICLES,
        **values,  # type: ignore[arg-type]
    )


def test_a_recorded_batch_is_journaled_with_its_number() -> None:
    found = batch()
    assert (str(found.number), found.status, found.cancellation) == (
        "IMP-000001",
        ImportStatus.IMPORTED,
        None,
    )
    assert [i.line for i in found.items] == [2, 3]  # triés par ligne
    [event] = found.events.pull()
    assert isinstance(event, ImportRecorded)
    record = event.audit_record()
    assert (record.action, record.module, record.entity.number) == (
        AuditAction.IMPORT,
        "import",
        "IMP-000001",
    )
    assert record.summary == "Import Articles IMP-000001 : 2 ligne(s) importée(s), 2 ignorée(s)"


def test_cancel_until_the_seventh_calendar_day_included() -> None:
    found = batch()
    assert (found.imported_on.isoformat(), found.last_cancel_day.isoformat()) == (
        "2026-11-10",
        "2026-11-17",
    )
    last_minute = datetime(2026, 11, 17, 22, 59, tzinfo=UTC)  # 17/11 23 h 59 à Douala
    found.cancel(performer=OWNER, now=last_minute)
    assert found.status is ImportStatus.CANCELLED
    assert found.cancellation is not None
    assert found.cancellation.by == OWNER.user_id
    events = found.events.pull()
    assert isinstance(events[-1], ImportCancelled)
    assert events[-1].audit_record().sensitive
    with pytest.raises(InvalidStateTransition):
        found.cancel(performer=OWNER, now=last_minute)


def test_cancel_on_the_eighth_day_is_too_late() -> None:
    found = batch()
    with pytest.raises(ImportCancelTooLate) as refused:
        found.cancel(performer=OWNER, now=datetime(2026, 11, 17, 23, 0, tzinfo=UTC))  # 18/11
    assert refused.value.code == "IMPORT_CANCEL_TOO_LATE"
    assert refused.value.details == {"imported_on": "2026-11-10", "last_day": "2026-11-17"}
    assert found.status is ImportStatus.IMPORTED


def test_invariants() -> None:
    with pytest.raises(ValueError, match="importées \\+ ignorées"):
        ImportCounts(rows_read=3, rows_imported=1, rows_ignored=1)
    with pytest.raises(ValueError, match="entiers positifs"):
        ImportCounts(rows_read=-1, rows_imported=0, rows_ignored=-1)
    with pytest.raises(ValueError, match="ligne de données"):
        ImportedItem(1, ImportedEntity.CUSTOMER, uuid7())
    with pytest.raises(ValueError, match="ligne de données"):
        ImportedItem(2, ImportedEntity.CUSTOMER, "pas un uuid")  # type: ignore[arg-type]
    twice = item(2)
    with pytest.raises(ValueError, match="deux fois"):
        batch(items=(twice, twice))
    with pytest.raises(ValueError, match="fichier source"):
        batch(source_file_key=" ")
    with pytest.raises(ValueError, match="IMP attendu"):
        ImportBatch.record(
            ShopId.new(), DocNumber(DocType.SALE, 1), ImportKind.SUPPLIERS,
            preview_id=ImportPreviewId.new(), source_file_key="k",
            counts=ImportCounts(rows_read=0, rows_imported=0, rows_ignored=0), items=(),
            performer=OWNER, now=IMPORTED,
        )  # fmt: skip
    found = batch()
    found.status = ImportStatus.CANCELLED
    with pytest.raises(ValueError, match="annulé"):
        found.__post_init__()


def test_labels_and_formats() -> None:
    assert [k.label for k in ImportKind] == [
        "Articles", "Stock de départ", "Clients", "Créances en cours", "Fournisseurs",
    ]  # fmt: skip
    assert isinstance(item(2).entity_id, UUID)
    assert IMPORTED + timedelta(days=7) > IMPORTED
