"""Dépôt SQL des pièces jointes (métadonnées ; contenu dans `FileStorage`)."""

from collections.abc import Collection
from typing import Any

import sqlalchemy as sa

from app.application.attachments.ports import AttachmentRepository
from app.domain.attachments.attachment import Attachment, AttachmentFile
from app.domain.attachments.values import AttachmentKind, FileFormat, OwnerType
from app.domain.catalog.ids import AttachmentId
from app.domain.shared.ids import ShopId, UserId
from app.infrastructure.persistence.sqlalchemy.columns import from_db, to_db
from app.infrastructure.persistence.sqlalchemy.repository import SqlRepository
from app.infrastructure.persistence.sqlalchemy.tables_attachments import attachment


class SqlAttachmentRepository(SqlRepository[AttachmentId, Attachment], AttachmentRepository):
    table = attachment

    def find_many(self, ids: Collection[AttachmentId]) -> list[Attachment]:
        wanted = sorted({ident.value for ident in ids})
        if not wanted:
            return []
        statement = sa.select(self.table).where(
            self.table.c.shop_id == self.shop_id.value, self.table.c.id.in_(wanted)
        )
        rows = self._transaction.fetch_all(statement)
        return self._tracked([self._from_row(row) for row in rows])

    def _to_columns(self, aggregate: Attachment) -> dict[str, Any]:
        file = aggregate.file
        return {
            "owner_type": file.owner_type.value,
            "owner_id": file.owner_id,
            "kind": file.kind.value,
            "mime": file.file_format.value,
            "size_bytes": file.size_bytes,
            "storage_key": aggregate.storage_key,
            "uploaded_by": aggregate.uploaded_by.value,
            "uploaded_at": to_db(aggregate.uploaded_at),
        }

    def _from_row(self, row: sa.RowMapping) -> Attachment:
        found = Attachment(
            id=AttachmentId(row["id"]),
            shop_id=ShopId(row["shop_id"]),
            file=AttachmentFile(
                owner_type=OwnerType(row["owner_type"]),
                owner_id=row["owner_id"],
                kind=AttachmentKind(row["kind"]),
                file_format=FileFormat(row["mime"]),
                size_bytes=int(row["size_bytes"]),
            ),
            uploaded_by=UserId(row["uploaded_by"]),
            uploaded_at=from_db(row["uploaded_at"]),
            version=int(row["version"]),
        )
        if found.storage_key != row["storage_key"]:
            msg = f"Pièce jointe {found.id} : clé de stockage incohérente en base"
            raise RuntimeError(msg)
        return found


SQL_ATTACHMENT_REPOSITORIES = (SqlAttachmentRepository,)
