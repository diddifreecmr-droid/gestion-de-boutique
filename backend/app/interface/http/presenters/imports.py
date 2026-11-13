"""Présentation de l'import : aperçu, lot, liste et détail des lots (UC-IMP-02, UC-IMP-03)."""

from collections import Counter

from app.application.imports.use_cases.preview_import import ImportPreview
from app.application.imports.use_cases.read_imports import ImportBatchView
from app.domain.imports.batch import ImportBatch
from app.interface.http.schemas import imports as s


def preview_response(preview: ImportPreview) -> s.ImportPreviewResponse:
    return s.ImportPreviewResponse(
        preview_id=str(preview.preview_id),
        kind=preview.kind,
        expires_at=preview.expires_at,
        rows_read=preview.rows_read,
        rows_valid=preview.rows_valid,
        rows_ignored=preview.rows_ignored,
        problems=[
            s.ImportProblemResponse(line=p.line, column=p.column, message=p.message, text=p.text)
            for p in preview.problems
        ],
        problems_total=preview.problems_total,
        notes=list(preview.notes),
    )


def _batch_fields(batch: ImportBatch) -> dict[str, object]:
    created = Counter(item.entity for item in batch.items)
    cancel = batch.cancellation
    return {
        "id": str(batch.id),
        "number": str(batch.number),
        "kind": batch.kind,
        "status": batch.status,
        "rows_read": batch.counts.rows_read,
        "rows_imported": batch.counts.rows_imported,
        "rows_ignored": batch.counts.rows_ignored,
        "created": [s.ImportCreatedCount(entity=e, count=n) for e, n in sorted(created.items())],
        "imported_at": batch.imported_at,
        "cancellable_until": batch.last_cancel_day,
        "cancelled_at": None if cancel is None else cancel.at,
    }


def batch_response(batch: ImportBatch) -> s.ImportBatchResponse:
    return s.ImportBatchResponse.model_validate(_batch_fields(batch))


def batch_list_response(batches: list[ImportBatch]) -> s.ImportBatchListResponse:
    return s.ImportBatchListResponse(items=[batch_response(batch) for batch in batches])


def batch_detail_response(view: ImportBatchView) -> s.ImportBatchDetailResponse:
    batch = view.batch
    return s.ImportBatchDetailResponse.model_validate(
        {
            **_batch_fields(batch),
            "imported_by": s.ImportAuthor(id=str(batch.imported_by), name=view.author_name),
            "problems_total": view.problems_total,
            "items": [
                s.ImportItemResponse(line=i.line, entity=i.entity, entity_id=str(i.entity_id))
                for i in batch.items
            ],
        }
    )
