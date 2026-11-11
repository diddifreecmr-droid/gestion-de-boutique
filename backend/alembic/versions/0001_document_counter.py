"""Compteurs de numérotation des documents (T06).

Révision : 0001
Précédente :
Créée le : 2026-11-11

Seule table de l'adaptateur de base : les tables métier arrivent avec leurs modules (T10+).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_counter",
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("doc_type", sa.String(length=8), nullable=False),
        sa.Column("last_value", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("shop_id", "doc_type", name=op.f("document_counter_pkey")),
        sa.CheckConstraint(
            "last_value >= 1", name=op.f("document_counter_last_value_positive_check")
        ),
        sa.CheckConstraint("version >= 1", name=op.f("document_counter_version_positive_check")),
    )


def downgrade() -> None:
    op.drop_table("document_counter")
