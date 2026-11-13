"""Routes de l'import (UC-IMP-01, UC-IMP-02) — specs § 6.3, sous `/shops/{shop_id}/…`.

Module `import` (`x-module`) : **à venir** jusqu'à T46, donc éteint pour toute boutique
(403 `MODULE_DISABLED` après le contrôle d'appartenance).

- `GET /imports/templates/{kind}` : modèle `.xlsx` (feuille de saisie, listes déroulantes,
  « Mode d'emploi ») ; modèle inconnu → 404 ; droit du modèle absent → 403.
- `POST /imports/preview` (multipart : `kind`, `file`) : aperçu sans écriture (200), fichier
  gardé 30 minutes sous `preview_id` ; 400 `IMPORT_FILE_INVALID`, 422 `IMPORT_TOO_MANY_ROWS`,
  503 si le stockage ne répond pas.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Response, UploadFile

from app.application.imports.use_cases.preview_import import ImportPreview, PreviewCommand
from app.application.security.actor import Actor
from app.domain.imports.values import MAX_FILE_BYTES, SpreadsheetFormat
from app.interface.http.routes.import_components import ImportsComponents
from app.interface.http.schemas.imports import ImportPreviewResponse, ImportProblemResponse

XLSX = SpreadsheetFormat.XLSX.value


def preview_response(preview: ImportPreview) -> ImportPreviewResponse:
    return ImportPreviewResponse(
        preview_id=str(preview.preview_id),
        kind=preview.kind,
        expires_at=preview.expires_at,
        rows_read=preview.rows_read,
        rows_valid=preview.rows_valid,
        rows_ignored=preview.rows_ignored,
        problems=[
            ImportProblemResponse(line=p.line, column=p.column, message=p.message, text=p.text)
            for p in preview.problems
        ],
        problems_total=preview.problems_total,
        notes=list(preview.notes),
    )


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
        headers = {
            "Content-Disposition": f'attachment; filename="{found.file_name}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        }
        return Response(found.content, media_type=found.media_type, headers=headers)

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

    return router
