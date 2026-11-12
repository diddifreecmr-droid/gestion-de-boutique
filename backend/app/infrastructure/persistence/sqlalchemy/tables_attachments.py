"""Table des pièces jointes (migration `0014_attachments`) — specs § 5.5 `ATTACHMENT`.

Métadonnées seulement : le contenu est dans le stockage objet (`FileStorage`), sous la clé
`storage_key` calculée par le domaine. `size_bytes` borné à 5 Mo (RG-T26) par un `CHECK`.
Index `(shop_id, owner_type, owner_id)` : pièces d'un élément. Aucune clé étrangère, comme
pour le reste du schéma (l'élément lié est vérifié par l'application).
"""

import sqlalchemy as sa

from app.infrastructure.persistence.sqlalchemy.schema import metadata

attachment = sa.Table(
    "attachment",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.Column("owner_type", sa.String(32), nullable=False),
    sa.Column("owner_id", sa.Uuid, nullable=True),
    sa.Column("kind", sa.String(32), nullable=False),
    sa.Column("mime", sa.String(64), nullable=False),
    sa.Column("size_bytes", sa.BigInteger, nullable=False),
    sa.Column("storage_key", sa.String(200), nullable=False),
    sa.Column("uploaded_by", sa.Uuid, nullable=False),
    sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("version >= 1", name="version_positive"),
    sa.CheckConstraint("size_bytes BETWEEN 1 AND 5242880", name="size_bytes_range"),
    sa.Index("attachment_shop_owner_idx", "shop_id", "owner_type", "owner_id"),
)
