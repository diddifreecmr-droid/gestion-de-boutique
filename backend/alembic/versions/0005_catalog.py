"""Catalogue : articles et historique des prix (T13).

Révision : 0005_catalog (après 0004_expenses)
Précédente : 0004_expenses
Créée le : 2026-11-11

- `article` : champs du profil dans `attributes` (JSON validé par le domaine) ; unicités par
  boutique sur les clés pliées `brand_model_key` (motos) et `reference_key` ; clés de recherche
  et de tri calculées ; montants `BIGINT` ≥ 0 ; index `(shop_id, sort_key, id)` ;
- `price_history` : ajout seul, index `(shop_id, article_id, effective_at)`.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_catalog"
down_revision: str | None = "0004_expenses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PRICES = ("base_price", "base_price_piece", "min_price", "min_price_piece", "last_cost", "wac")


def upgrade() -> None:
    op.create_table(
        "article",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("display_name", sa.String(length=250), nullable=False),
        sa.Column("brand", sa.String(length=120), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("brand_model_key", sa.String(length=250), nullable=True),
        sa.Column("reference_key", sa.String(length=250), nullable=True),
        sa.Column("search_key", sa.String(length=250), nullable=False),
        sa.Column("sort_key", sa.String(length=250), nullable=False),
        sa.Column("stock_unit", sa.String(length=8), nullable=False),
        sa.Column("sold_by_piece", sa.Boolean(), nullable=False),
        sa.Column("piece_length_m", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("alert_threshold", sa.Numeric(precision=12, scale=1), nullable=True),
        sa.Column("photo_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False),
        *(sa.Column(name, sa.BigInteger(), nullable=True) for name in _PRICES),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version >= 1", name=op.f("article_version_positive_check")),
        *(
            sa.CheckConstraint(f"{name} >= 0", name=op.f(f"article_{name}_non_negative_check"))
            for name in _PRICES
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("article_pkey")),
        sa.UniqueConstraint("shop_id", "brand_model_key", name="article_brand_model"),
        sa.UniqueConstraint("shop_id", "reference_key", name="article_reference"),
    )
    op.create_index("article_shop_sort_idx", "article", ["shop_id", "sort_key", "id"], unique=False)
    op.create_table(
        "price_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("price_kind", sa.String(length=24), nullable=False),
        sa.Column("old_price", sa.BigInteger(), nullable=True),
        sa.Column("new_price", sa.BigInteger(), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("price_history_pkey")),
    )
    op.create_index(
        "price_history_article_idx",
        "price_history",
        ["shop_id", "article_id", "effective_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("price_history_article_idx", table_name="price_history")
    op.drop_table("price_history")
    op.drop_index("article_shop_sort_idx", table_name="article")
    op.drop_table("article")
