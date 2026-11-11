"""Stock : projection, grand livre, ajustements, inventaires (T14).

Révision : 0006_stock (après 0005_catalog)
Précédente : 0005_catalog
Créée le : 2026-11-11

- `stock_level` : une ligne par article x lieu (`stock_level_article_location`), `version` ;
- `stock_movement` : grand livre en ajout seul, une annulation par mouvement au plus
  (`stock_movement_reverses`) ;
- `stock_adjustment` : ajustements (quantité > 0) ;
- `inventory` (+ `inventory_line`) : un seul inventaire en cours par lieu
  (`inventory_open_location`), numéro unique par boutique.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_stock"
down_revision: str | None = "0005_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TS = sa.DateTime(timezone=True)


def _qty() -> sa.Numeric[object]:
    return sa.Numeric(precision=12, scale=1)


def upgrade() -> None:
    op.create_table(
        "stock_level",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("unit", sa.String(length=8), nullable=False),
        sa.Column("sellable", _qty(), nullable=False),
        sa.Column("damaged", _qty(), nullable=False),
        sa.Column("incoming", _qty(), nullable=False),
        sa.CheckConstraint("version >= 1", name=op.f("stock_level_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("stock_level_pkey")),
        sa.UniqueConstraint(
            "shop_id", "article_id", "location_id", name="stock_level_article_location"
        ),
    )
    op.create_index(
        "stock_level_shop_location_idx", "stock_level", ["shop_id", "location_id"], unique=False
    )
    op.create_table(
        "stock_movement",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=24), nullable=False),
        sa.Column("condition", sa.String(length=16), nullable=False),
        sa.Column("unit", sa.String(length=8), nullable=False),
        sa.Column("quantity", _qty(), nullable=False),
        sa.Column("balance_after", _qty(), nullable=False),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("source_number", sa.String(length=64), nullable=True),
        sa.Column("unit_cost", sa.BigInteger(), nullable=True),
        sa.Column("occurred_at", _TS, nullable=False),
        sa.Column("recorded_at", _TS, nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("stock_to_verify", sa.Boolean(), nullable=False),
        sa.Column("reverses_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("quantity <> 0", name=op.f("stock_movement_quantity_non_zero_check")),
        sa.CheckConstraint(
            "unit_cost >= 0", name=op.f("stock_movement_unit_cost_non_negative_check")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("stock_movement_pkey")),
        sa.UniqueConstraint("shop_id", "reverses_id", name="stock_movement_reverses"),
    )
    for name, columns in (
        ("stock_movement_article_idx", ["shop_id", "article_id", "occurred_at", "id"]),
        ("stock_movement_location_idx", ["shop_id", "location_id", "type", "recorded_at"]),
        ("stock_movement_source_idx", ["shop_id", "source_id"]),
    ):
        op.create_index(name, "stock_movement", columns, unique=False)
    op.create_table(
        "stock_adjustment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("unit", sa.String(length=8), nullable=False),
        sa.Column("quantity", _qty(), nullable=False),
        sa.Column("condition", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=24), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("photo_id", sa.Uuid(), nullable=True),
        sa.Column("inventory_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", _TS, nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("version >= 1", name=op.f("stock_adjustment_version_positive_check")),
        sa.CheckConstraint("quantity > 0", name=op.f("stock_adjustment_quantity_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("stock_adjustment_pkey")),
    )
    op.create_index(
        "stock_adjustment_article_idx",
        "stock_adjustment",
        ["shop_id", "article_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "inventory",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("number", sa.String(length=32), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("open_location_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", _TS, nullable=False),
        sa.Column("closed_at", _TS, nullable=True),
        sa.Column("global_reason", sa.String(length=500), nullable=True),
        sa.CheckConstraint("version >= 1", name=op.f("inventory_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("inventory_pkey")),
        sa.UniqueConstraint("shop_id", "number", name="inventory_number"),
        sa.UniqueConstraint("shop_id", "open_location_id", name="inventory_open_location"),
    )
    op.create_table(
        "inventory_line",
        sa.Column("inventory_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("unit", sa.String(length=8), nullable=False),
        sa.Column("counted", _qty(), nullable=True),
        sa.Column("theoretical", _qty(), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("gap_value", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("inventory_id", "article_id", name=op.f("inventory_line_pkey")),
    )


def downgrade() -> None:
    op.drop_table("inventory_line")
    op.drop_table("inventory")
    op.drop_index("stock_adjustment_article_idx", table_name="stock_adjustment")
    op.drop_table("stock_adjustment")
    for name in (
        "stock_movement_source_idx",
        "stock_movement_location_idx",
        "stock_movement_article_idx",
    ):
        op.drop_index(name, table_name="stock_movement")
    op.drop_table("stock_movement")
    op.drop_index("stock_level_shop_location_idx", table_name="stock_level")
    op.drop_table("stock_level")
