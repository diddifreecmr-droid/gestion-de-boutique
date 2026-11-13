"""Tables de l'import (migration `0019_import_batches`) — specs § 5.5 `IMPORT_BATCH`.

- `import_batch` : numéro `IMP-…` unique par boutique (`import_batch_number`), aperçu confirmé
  unique (`import_batch_preview` : confirmation idempotente), clé du fichier source dans le
  stockage, compteurs de lignes (`importées + ignorées = lues`), statut et annulation.
- `import_item` : chaque élément créé par le lot (type, identifiant, ligne du fichier),
  **réécrit** avec le lot ; index `(shop_id, entity_type, entity_id)` : retrouver le lot d'un
  élément (annulation et blocages, QC-6, T35).
- Aucune clé étrangère, comme pour le reste du schéma.
"""

import sqlalchemy as sa

from app.infrastructure.persistence.sqlalchemy.schema import metadata

_TS = sa.DateTime(timezone=True)

import_batch = sa.Table(
    "import_batch",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.Column("number", sa.String(16), nullable=False),
    sa.Column("kind", sa.String(32), nullable=False),
    sa.Column("preview_id", sa.Uuid, nullable=False),
    sa.Column("source_file_key", sa.String(200), nullable=False),
    sa.Column("rows_read", sa.Integer, nullable=False),
    sa.Column("rows_imported", sa.Integer, nullable=False),
    sa.Column("rows_ignored", sa.Integer, nullable=False),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("imported_by", sa.Uuid, nullable=False),
    sa.Column("imported_at", _TS, nullable=False),
    sa.Column("cancelled_at", _TS, nullable=True),
    sa.Column("cancelled_by", sa.Uuid, nullable=True),
    sa.UniqueConstraint("shop_id", "number", name="import_batch_number"),
    sa.UniqueConstraint("shop_id", "preview_id", name="import_batch_preview"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
    sa.CheckConstraint("rows_imported + rows_ignored = rows_read", name="rows_balanced"),
    sa.CheckConstraint("status IN ('imported', 'cancelled')", name="status_known"),
    sa.Index("import_batch_shop_imported_idx", "shop_id", "imported_at"),
)

import_item = sa.Table(
    "import_item",
    metadata,
    sa.Column("import_batch_id", sa.Uuid, primary_key=True),
    sa.Column("position", sa.Integer, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("line", sa.Integer, nullable=False),
    sa.Column("entity_type", sa.String(32), nullable=False),
    sa.Column("entity_id", sa.Uuid, nullable=False),
    sa.CheckConstraint("line >= 2", name="line_of_data"),
    sa.Index("import_item_shop_entity_idx", "shop_id", "entity_type", "entity_id"),
)
