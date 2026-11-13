"""Routes de l'import (UC-IMP-01 à UC-IMP-03) — specs § 6.3, sous `/shops/{shop_id}/…`.

Module `import` (`x-module`) : **à venir** jusqu'à T46, donc éteint pour toute boutique
(403 `MODULE_DISABLED` après le contrôle d'appartenance).

- `GET /imports/templates/{kind}` : modèle `.xlsx` ; modèle inconnu → 404 ; droit absent → 403.
- `POST /imports/preview` (multipart : `kind`, `file`) : aperçu sans écriture (200) ; 400
  `IMPORT_FILE_INVALID`, 422 `IMPORT_TOO_MANY_ROWS`, 503 si le stockage ne répond pas.
- `POST /imports` (`preview_id`) : 201 et le lot `IMP-…` ; rejoué → 200 et le même lot ; 404,
  410 `IMPORT_PREVIEW_EXPIRED`, 422 (aucune ligne valide).
- `GET /imports`, `GET /imports/{id}`, `GET /imports/{id}/errors.xlsx` (T35) : lots des modèles
  de l'utilisateur (M3-03), détail, rapport des lignes refusées.
- `POST /imports/{id}/cancel` (T35, QC-6) : propriétaire ; 422 `IMPORT_CANCEL_TOO_LATE`,
  `IMPORT_CANCEL_BLOCKED` (`details.blocking`), `INVALID_STATE_TRANSITION` (déjà annulé).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Response, UploadFile, status

from app.application.imports.use_cases.confirm_import import ConfirmCommand
from app.application.imports.use_cases.preview_import import PreviewCommand
from app.application.security.actor import Actor
from app.domain.imports.ids import ImportBatchId, ImportPreviewId
from app.domain.imports.values import MAX_FILE_BYTES, SpreadsheetFormat
from app.interface.http.presenters.imports import (
    batch_detail_response,
    batch_list_response,
    batch_response,
    preview_response,
)
from app.interface.http.routes.import_components import ImportsComponents
from app.interface.http.schemas.imports import (
    ImportBatchDetailResponse,
    ImportBatchListResponse,
    ImportBatchResponse,
    ImportConfirmRequest,
    ImportPreviewResponse,
)

XLSX = SpreadsheetFormat.XLSX.value


def _file(content: bytes, media_type: str, file_name: str) -> Response:
    headers = {
        "Content-Disposition": f'attachment; filename="{file_name}"',
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content, media_type=media_type, headers=headers)


def build_imports_router(c: ImportsComponents) -> APIRouter:
    router = APIRouter(tags=["imports"])
    Member = Annotated[Actor, Depends(c.guard.current_actor)]  # noqa: N806

    @router.get(
        "/shops/{shop_id}/imports/templates/{kind}",
        response_class=Response,
        responses={200: {"content": {XLSX: {}}}},
    )
    def download_template(actor: Member, kind: str) -> Response:
        found = c.template.execute(actor, kind)
        return _file(found.content, found.media_type, found.file_name)

    @router.post("/shops/{shop_id}/imports/preview", operation_id="preview_import")
    def preview(
        actor: Member,
        response: Response,
        file: UploadFile,
        kind: Annotated[str, Form(max_length=32)],
    ) -> ImportPreviewResponse:
        content = file.file.read(MAX_FILE_BYTES + 1)  # au-delà : refus sans tout lire
        command = PreviewCommand(kind=kind, content=content, file_name=file.filename)
        response.headers["Cache-Control"] = "no-store"
        return preview_response(c.preview.execute(actor, command))

    @router.post(
        "/shops/{shop_id}/imports",
        operation_id="confirm_import",
        status_code=status.HTTP_201_CREATED,
    )
    def confirm(
        actor: Member, body: ImportConfirmRequest, response: Response
    ) -> ImportBatchResponse:
        command = ConfirmCommand(preview_id=ImportPreviewId.parse(body.preview_id))
        batch, created = c.confirm.execute(actor, command)
        if not created:
            response.status_code = status.HTTP_200_OK
        return batch_response(batch)

    @router.get("/shops/{shop_id}/imports", operation_id="list_imports")
    def list_imports(actor: Member) -> ImportBatchListResponse:
        return batch_list_response(c.read.list(actor))

    @router.get("/shops/{shop_id}/imports/{batch_id}", operation_id="get_import")
    def get_import(actor: Member, batch_id: str) -> ImportBatchDetailResponse:
        return batch_detail_response(c.read.get(actor, ImportBatchId.parse(batch_id)))

    @router.get(
        "/shops/{shop_id}/imports/{batch_id}/errors.xlsx",
        operation_id="download_import_errors",
        response_class=Response,
        responses={200: {"content": {XLSX: {}}}},
    )
    def download_errors(actor: Member, batch_id: str) -> Response:
        found = c.read.errors(actor, ImportBatchId.parse(batch_id))
        return _file(found.content, found.media_type, found.file_name)

    @router.post("/shops/{shop_id}/imports/{batch_id}/cancel", operation_id="cancel_import")
    def cancel(actor: Member, batch_id: str) -> ImportBatchResponse:
        return batch_response(c.cancel.execute(actor, ImportBatchId.parse(batch_id)))

    return router
