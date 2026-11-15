"""Tissu d'un article textile : un article par couleur, regroupés par tissu (2026-11-15).

Révision : 0021_article_fabric
Précédente : 0020_import_cancellation
Créée le : 2026-11-15

- `article.fabric` : nom du tissu saisi (« Djampar ») ; `NULL` hors Textile et pour les
  articles textiles créés avant (aucune reprise : ils restent des articles sans tissu).
- `article.fabric_key` : tissu plié (domaine, `ArticleDetails.fabric_key`), filtre de
  `GET /articles?fabric=` et des mises à jour d'un tissu ; index `(shop_id, fabric_key)`.
  **Pas** d'unicité : un tissu a plusieurs couleurs (l'unicité du nom reste `article_name`).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021_article_fabric"
down_revision: str | None = "0020_import_cancellation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("article", sa.Column("fabric", sa.String(length=120), nullable=True))
    op.add_column("article", sa.Column("fabric_key", sa.String(length=250), nullable=True))
    op.create_index("article_shop_fabric_idx", "article", ["shop_id", "fabric_key"])


def downgrade() -> None:
    op.drop_index("article_shop_fabric_idx", table_name="article")
    op.drop_column("article", "fabric_key")
    op.drop_column("article", "fabric")
