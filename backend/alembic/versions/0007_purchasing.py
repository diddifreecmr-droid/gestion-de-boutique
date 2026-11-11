"""Achats : fournisseurs, achats, lignes chiffrées, frais, paiements fournisseur (T15).

Révision : 0007_purchasing (après 0006_stock)
Précédente : 0006_stock
Créée le : 2026-11-11

- `supplier` : nom unique sans casse par boutique (`supplier_name`) ;
- `purchase` : numéro unique par boutique (`purchase_number`), index sur la date d'achat ;
- `purchase_line`, `purchase_fee`, `supplier_payment` : enfants réécrits avec l'achat.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_purchasing"
down_revision: str | None = "0006_stock"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "purchase",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("number", sa.String(length=16), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("entry_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_ref", sa.String(length=64), nullable=True),
        sa.Column("invoice_photo_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("merchandise_total", sa.BigInteger(), nullable=False),
        sa.Column("fees_total", sa.BigInteger(), nullable=False),
        sa.Column("total", sa.BigInteger(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.Uuid(), nullable=True),
        sa.Column("cancel_reason", sa.String(length=500), nullable=True),
        sa.CheckConstraint("total >= 0", name=op.f("purchase_total_non_negative_check")),
        sa.CheckConstraint("version >= 1", name=op.f("purchase_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("purchase_pkey")),
        sa.UniqueConstraint("shop_id", "number", name="purchase_number"),
    )
    op.create_index(
        "purchase_shop_date_idx", "purchase", ["shop_id", "purchase_date"], unique=False
    )
    op.create_index(
        "purchase_shop_supplier_idx", "purchase", ["shop_id", "supplier_id"], unique=False
    )
    op.create_table(
        "purchase_fee",
        sa.Column("purchase_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("amount >= 0", name=op.f("purchase_fee_amount_non_negative_check")),
        sa.PrimaryKeyConstraint("purchase_id", "position", name=op.f("purchase_fee_pkey")),
    )
    op.create_table(
        "purchase_line",
        sa.Column("purchase_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("entered_qty", sa.Numeric(precision=12, scale=1), nullable=False),
        sa.Column("entered_unit", sa.String(length=8), nullable=False),
        sa.Column("stock_unit", sa.String(length=8), nullable=False),
        sa.Column("stock_qty", sa.Numeric(precision=12, scale=1), nullable=False),
        sa.Column("unit_price", sa.BigInteger(), nullable=False),
        sa.Column("line_total", sa.BigInteger(), nullable=False),
        sa.Column("fee_share", sa.BigInteger(), nullable=False),
        sa.Column("final_unit_cost", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "entered_qty > 0", name=op.f("purchase_line_entered_qty_positive_check")
        ),
        sa.CheckConstraint(
            "unit_price >= 0", name=op.f("purchase_line_unit_price_non_negative_check")
        ),
        sa.PrimaryKeyConstraint("purchase_id", "position", name=op.f("purchase_line_pkey")),
    )
    op.create_index(
        "purchase_line_article_idx", "purchase_line", ["shop_id", "article_id"], unique=False
    )
    op.create_table(
        "supplier",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_key", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=120), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version >= 1", name=op.f("supplier_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("supplier_pkey")),
        sa.UniqueConstraint("shop_id", "name_key", name="supplier_name"),
    )
    op.create_table(
        "supplier_payment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("purchase_id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("mode_id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint("amount > 0", name=op.f("supplier_payment_amount_positive_check")),
        sa.PrimaryKeyConstraint("purchase_id", "position", name=op.f("supplier_payment_pkey")),
    )
    op.create_index(
        "supplier_payment_purchase_idx",
        "supplier_payment",
        ["shop_id", "purchase_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("supplier_payment_purchase_idx", table_name="supplier_payment")
    op.drop_table("supplier_payment")
    op.drop_table("supplier")
    op.drop_index("purchase_line_article_idx", table_name="purchase_line")
    op.drop_table("purchase_line")
    op.drop_table("purchase_fee")
    op.drop_index("purchase_shop_supplier_idx", table_name="purchase")
    op.drop_index("purchase_shop_date_idx", table_name="purchase")
    op.drop_table("purchase")
