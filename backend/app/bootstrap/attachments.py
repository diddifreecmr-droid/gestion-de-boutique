"""Assemblage des pièces jointes (TR-17, D16) : stockage configuré, liens signés, routes.

- `STORAGE_BACKEND=memory` (tests, démo) ou `s3` (Silo en prod, réseau interne) ; le client S3
  n'ouvre aucune connexion à l'assemblage : une panne de Silo ne bloque pas le démarrage, elle
  rend `503 STORAGE_UNAVAILABLE` à l'envoi et à la lecture (specs § 9).
- Clé des liens signés dérivée de `JWT_SECRET` (aucun secret de plus à gérer) ; durée
  `ATTACHMENT_LINK_TTL_SECONDS`.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import assert_never

from app.application.attachments.access import AttachmentAccess
from app.application.attachments.links import LinkSigner, derive_link_key
from app.application.attachments.ports import FileStorage
from app.application.attachments.use_cases.issue_link import IssueAttachmentLink
from app.application.attachments.use_cases.read_content import ReadAttachmentContent
from app.application.attachments.use_cases.upload_attachment import UploadAttachment
from app.application.security.policy import Policy
from app.bootstrap.config import Settings
from app.bootstrap.identity import IdentityModule
from app.bootstrap.storage_config import StorageBackend
from app.infrastructure.storage.memory import MemoryFileStorage
from app.infrastructure.storage.s3 import S3FileStorage, S3Location
from app.interface.http.routes.attachment_components import AttachmentsComponents


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentsModule:
    http: AttachmentsComponents
    storage: FileStorage


def build_storage(settings: Settings) -> FileStorage:
    backend = settings.storage_backend
    if backend is StorageBackend.MEMORY:
        return MemoryFileStorage()
    if backend is StorageBackend.S3:
        endpoint, access, secret, bucket = (
            settings.S3_ENDPOINT,
            settings.S3_ACCESS_KEY,
            settings.S3_SECRET_KEY,
            settings.S3_BUCKET,
        )
        if endpoint is None or access is None or secret is None or bucket is None:
            msg = "Variables S3_* manquantes avec STORAGE_BACKEND=s3"  # refusé par Settings
            raise RuntimeError(msg)
        location = S3Location(
            endpoint=endpoint,
            access_key=access,
            secret_key=secret.get_secret_value(),
            bucket=bucket,
            region=settings.S3_REGION,
        )
        return S3FileStorage(location)
    assert_never(backend)


def build_attachments(
    settings: Settings, identity: IdentityModule, storage: FileStorage | None = None
) -> AttachmentsModule:
    """`storage` : imposé par les tests (mémoire en panne, Silo de dev), sinon configuré."""
    uows, clock = identity.core.shop_uow_factory, identity.clock
    files = build_storage(settings) if storage is None else storage
    key = derive_link_key(settings.JWT_SECRET.get_secret_value().encode("utf-8"))
    signer = LinkSigner(key, timedelta(seconds=settings.ATTACHMENT_LINK_TTL_SECONDS))
    access = AttachmentAccess(Policy(clock=clock.now))
    http = AttachmentsComponents(
        upload=UploadAttachment(uows, access, clock, files),
        issue_link=IssueAttachmentLink(uows, access, clock, signer),
        read_content=ReadAttachmentContent(uows, clock, signer, files),
        guard=identity.auth.guard,
    )
    return AttachmentsModule(http=http, storage=files)
