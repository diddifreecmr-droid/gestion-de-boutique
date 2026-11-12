"""Routes des pièces jointes (TR-17, RG-T26, UC-CRE-07) — specs § 6.3, sous `/shops/{shop_id}/…`.

- `POST /attachments` (multipart : `file`, `owner_type`, `owner_id`, `kind`, `id` facultatif) :
  201, ou 200 au rejeu d'un `id` déjà enregistré ; 400 format ou taille ; 503 stockage absent.
- `GET /attachments/{id}/url` : lien signé de `ATTACHMENT_LINK_TTL_SECONDS` (60 s), délivré
  **après** contrôle des droits (403 permission, 404 hors portée ou autre boutique).
- `GET /attachments/{id}/content?expires=&signature=` : contenu relayé par l'API (le stockage
  n'est jamais exposé) ; sans jeton, le lien signé suffit ; 404 signature fausse, 410 expiré.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Query, Response, UploadFile, status

from app.application.attachments.use_cases.upload_attachment import UploadCommand
from app.application.security.actor import Actor
from app.domain.attachments.attachment import Attachment
from app.domain.attachments.values import MAX_SIZE_BYTES, AttachmentKind, OwnerType
from app.domain.catalog.ids import AttachmentId
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import ShopId
from app.interface.http.routes.attachment_components import AttachmentsComponents
from app.interface.http.schemas.attachments import AttachmentLinkResponse, AttachmentResponse

ATTACHMENT = "/shops/{shop_id}/attachments/{attachment_id}"


def _owner_id(text: str | None) -> UUID | None:
    if text is None or not text.strip():
        return None
    try:
        return UUID(text.strip())
    except ValueError as exc:
        msg = "Identifiant de l'élément lié illisible"
        raise ValidationFailed(msg, details={"field": "owner_id"}) from exc


def attachment_response(attachment: Attachment) -> AttachmentResponse:
    file = attachment.file
    return AttachmentResponse(
        id=str(attachment.id),
        owner_type=file.owner_type,
        owner_id=None if file.owner_id is None else str(file.owner_id),
        kind=file.kind,
        mime=file.file_format,
        size_bytes=file.size_bytes,
        uploaded_at=attachment.uploaded_at,
    )


def build_attachments_router(c: AttachmentsComponents, api_prefix: str) -> APIRouter:
    router = APIRouter(tags=["attachments"])
    Member = Annotated[Actor, Depends(c.guard.current_actor)]  # noqa: N806
    FormId = Annotated[str | None, Form(max_length=64)]  # noqa: N806

    @router.post(
        "/shops/{shop_id}/attachments",
        status_code=status.HTTP_201_CREATED,
        operation_id="upload_attachment",  # schéma du corps : « Body_upload_attachment »
    )
    def upload(
        actor: Member,
        response: Response,
        file: UploadFile,
        owner_type: Annotated[OwnerType, Form()],
        kind: Annotated[AttachmentKind, Form()],
        owner_id: FormId = None,
        id: FormId = None,  # identifiant client : rejeu idempotent (§ 6.1)
    ) -> AttachmentResponse:
        content = file.file.read(MAX_SIZE_BYTES + 1)  # au-delà : refus sans tout lire
        command = UploadCommand(
            owner_type=owner_type,
            owner_id=_owner_id(owner_id),
            kind=kind,
            content=content,
            attachment_id=None if id is None else AttachmentId.parse(id),
        )
        attachment, created = c.upload.execute(actor, command)
        if not created:
            response.status_code = status.HTTP_200_OK
        return attachment_response(attachment)

    @router.get(f"{ATTACHMENT}/url")
    def issue_link(actor: Member, attachment_id: str, response: Response) -> AttachmentLinkResponse:
        issued = c.issue_link.execute(actor, AttachmentId.parse(attachment_id))
        response.headers["Cache-Control"] = "no-store"
        link, file = issued.link, issued.attachment.file
        path = f"{api_prefix}/shops/{link.shop_id}/attachments/{link.attachment_id}/content"
        return AttachmentLinkResponse(
            url=f"{path}?expires={link.expires}&signature={link.signature}",
            expires_at=link.expires_at,
            mime=file.file_format,
            kind=file.kind,
        )

    @router.get(
        f"{ATTACHMENT}/content",
        response_class=Response,
        responses={200: {"content": {"image/jpeg": {}, "image/png": {}, "application/pdf": {}}}},
    )
    def read_content(
        shop_id: str,
        attachment_id: str,
        expires: Annotated[int, Query(ge=0)],
        signature: Annotated[str, Query(min_length=16, max_length=128)],
    ) -> Response:
        found = c.read_content.execute(
            ShopId.parse(shop_id), AttachmentId.parse(attachment_id), expires, signature
        )
        file = found.attachment.file
        name = f"piece-jointe-{found.attachment.id}.{file.file_format.extension}"
        headers = {
            "Content-Disposition": f'inline; filename="{name}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        }
        return Response(found.content, media_type=file.file_format.value, headers=headers)

    return router
