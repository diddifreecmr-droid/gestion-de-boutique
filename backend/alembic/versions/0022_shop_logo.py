"""Logo de la boutique (décision client 2026-11-24, specs § 15.1).

Révision : 0022_shop_logo
Précédente : 0021_article_fabric
Créée le : 2026-11-24

- `shop_settings.logo_attachment_id` : pièce jointe `shop` (JPG ou PNG) désignée par le gérant ;
  `NULL` = pas de logo (logo générique aux initiales côté frontend). Aucune clé étrangère,
  comme les autres références aux pièces jointes (`attachment` n'est jamais supprimée).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0022_shop_logo"
down_revision: str | None = "0021_article_fabric"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("shop_settings", sa.Column("logo_attachment_id", sa.Uuid(), nullable=True))


def downgrade() -> None:
    op.drop_column("shop_settings", "logo_attachment_id")
