"""Pièces jointes : métadonnées des fichiers du stockage objet (TR-17, RG-T26, specs § 5.5).

Révision : 0014_attachments
Précédente : 0013_sync
Créée le : 2026-11-12

- `attachment` : élément lié (`owner_type`, `owner_id`), type, format reconnu (`mime`), taille
  (1 octet à 5 Mo, `CHECK`), clé de l'objet dans le bucket privé, auteur et instant de l'envoi.
  Le contenu n'est jamais en base.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014_attachments"
down_revision: str | None = "0013_sync"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attachment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("owner_type", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("mime", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(length=200), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version >= 1", name=op.f("attachment_version_positive_check")),
        sa.CheckConstraint(
            "size_bytes BETWEEN 1 AND 5242880", name=op.f("attachment_size_bytes_range_check")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("attachment_pkey")),
    )
    op.create_index(
        "attachment_shop_owner_idx", "attachment", ["shop_id", "owner_type", "owner_id"]
    )


def downgrade() -> None:
    op.drop_index("attachment_shop_owner_idx", table_name="attachment")
    op.drop_table("attachment")
