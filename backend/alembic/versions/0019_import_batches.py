"""Lots d'import : `import_batch` et les éléments créés `import_item` (TR-22, specs § 5.5).

Révision : 0019_import_batches
Précédente : 0018_exchange_rights (T29, développée en parallèle ; fusion dans l'ordre)
Créée le : 2026-11-13

- `import_batch` : numéro `IMP-…` et aperçu confirmé uniques par boutique, fichier source
  (clé du stockage), compteurs de lignes équilibrés, statut `imported | cancelled`,
  annulation (instant, auteur) — QC-6 : rien n'est effacé, l'annulation archive.
- `import_item` : élément créé (type, identifiant, ligne du fichier), index pour retrouver
  le lot d'un élément.

Aucune donnée existante n'est touchée ; le retour arrière supprime les deux tables.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019_import_batches"
down_revision: str | None = "0018_exchange_rights"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "import_batch",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("number", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("preview_id", sa.Uuid(), nullable=False),
        sa.Column("source_file_key", sa.String(length=200), nullable=False),
        sa.Column("rows_read", sa.Integer(), nullable=False),
        sa.Column("rows_imported", sa.Integer(), nullable=False),
        sa.Column("rows_ignored", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("imported_by", sa.Uuid(), nullable=False),
        sa.Column("imported_at", _TS, nullable=False),
        sa.Column("cancelled_at", _TS, nullable=True),
        sa.Column("cancelled_by", sa.Uuid(), nullable=True),
        sa.CheckConstraint("version >= 1", name=op.f("import_batch_version_positive_check")),
        sa.CheckConstraint(
            "rows_imported + rows_ignored = rows_read",
            name=op.f("import_batch_rows_balanced_check"),
        ),
        sa.CheckConstraint(
            "status IN ('imported', 'cancelled')", name=op.f("import_batch_status_known_check")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("import_batch_pkey")),
        sa.UniqueConstraint("shop_id", "number", name="import_batch_number"),
        sa.UniqueConstraint("shop_id", "preview_id", name="import_batch_preview"),
    )
    op.create_index("import_batch_shop_imported_idx", "import_batch", ["shop_id", "imported_at"])
    op.create_table(
        "import_item",
        sa.Column("import_batch_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("line", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("line >= 2", name=op.f("import_item_line_of_data_check")),
        sa.PrimaryKeyConstraint("import_batch_id", "position", name=op.f("import_item_pkey")),
    )
    op.create_index(
        "import_item_shop_entity_idx", "import_item", ["shop_id", "entity_type", "entity_id"]
    )


def downgrade() -> None:
    op.drop_index("import_item_shop_entity_idx", table_name="import_item")
    op.drop_table("import_item")
    op.drop_index("import_batch_shop_imported_idx", table_name="import_batch")
    op.drop_table("import_batch")
