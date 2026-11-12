"""Cas d'utilisation des pièces jointes, assemblés par la composition root (TR-17)."""

from dataclasses import dataclass

from app.application.attachments.use_cases.issue_link import IssueAttachmentLink
from app.application.attachments.use_cases.read_content import ReadAttachmentContent
from app.application.attachments.use_cases.upload_attachment import UploadAttachment
from app.interface.http.security import AuthGuard


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentsComponents:
    upload: UploadAttachment
    issue_link: IssueAttachmentLink
    read_content: ReadAttachmentContent
    guard: AuthGuard
