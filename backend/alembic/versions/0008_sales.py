"""Ventes : clients, ventes, lignes à coûts figés, détails vendus, paiements, châssis réservés,
signalements d'erreur, impressions de reçus (T16a).

Révision : 0008_sales (après 0007_purchasing)
Précédente : 0007_purchasing
Créée le : 2026-11-11

- `customer` : téléphone E.164 unique par boutique (`customer_phone`) ;
- `sale` : numéro unique par boutique (`sale_number`), index date, vendeur, client, annulation ;
- `sale_line`, `sold_detail`, `sale_payment` : enfants réécrits avec la vente ;
- `sold_chassis` : châssis réservé par une vente non annulée (`sold_chassis_active`, RG-M01) ;
- `sale_error_report`, `receipt_print` (`receipt_print_sequence`).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_sales"
down_revision: str | None = "0007_purchasing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customer",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("city", sa.String(length=200), nullable=True),
        sa.Column("address", sa.String(length=200), nullable=True),
        sa.Column("id_doc_type", sa.String(length=32), nullable=True),
        sa.Column("id_doc_number", sa.String(length=200), nullable=True),
        sa.Column("id_doc_photo_id", sa.Uuid(), nullable=True),
        sa.Column("credit_limit", sa.BigInteger(), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("search_key", sa.String(length=250), nullable=False),
        sa.Column("sort_key", sa.String(length=250), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "credit_limit >= 0", name=op.f("customer_credit_limit_non_negative_check")
        ),
        sa.CheckConstraint("version >= 1", name=op.f("customer_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("customer_pkey")),
        sa.UniqueConstraint("shop_id", "phone", name="customer_phone"),
    )
    op.create_index("customer_shop_sort_idx", "customer", ["shop_id", "sort_key"], unique=False)
    op.create_table(
        "receipt_print",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("sale_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("printed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("printed_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint("sequence >= 1", name=op.f("receipt_print_sequence_positive_check")),
        sa.CheckConstraint("version >= 1", name=op.f("receipt_print_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("receipt_print_pkey")),
        sa.UniqueConstraint("shop_id", "sale_id", "sequence", name="receipt_print_sequence"),
    )
    op.create_table(
        "sale",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("number", sa.String(length=16), nullable=False),
        sa.Column("provisional_number", sa.String(length=32), nullable=True),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("seller_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=True),
        sa.Column("sold_on", sa.Date(), nullable=False),
        sa.Column("sold_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total", sa.BigInteger(), nullable=False),
        sa.Column("paid", sa.BigInteger(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("reminder_on", sa.Date(), nullable=True),
        sa.Column("credit_terms", sa.String(length=500), nullable=True),
        sa.Column("stock_to_verify", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.Uuid(), nullable=True),
        sa.Column("cancel_reason", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "paid >= 0 AND paid <= total", name=op.f("sale_paid_within_total_check")
        ),
        sa.CheckConstraint("version >= 1", name=op.f("sale_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("sale_pkey")),
        sa.UniqueConstraint("shop_id", "number", name="sale_number"),
    )
    op.create_index("sale_shop_cancelled_idx", "sale", ["shop_id", "cancelled_at"], unique=False)
    op.create_index("sale_shop_customer_idx", "sale", ["shop_id", "customer_id"], unique=False)
    op.create_index("sale_shop_date_idx", "sale", ["shop_id", "sold_on"], unique=False)
    op.create_index(
        "sale_shop_provisional_idx", "sale", ["shop_id", "provisional_number"], unique=False
    )
    op.create_index(
        "sale_shop_seller_idx", "sale", ["shop_id", "seller_id", "sold_on"], unique=False
    )
    op.create_table(
        "sale_error_report",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("sale_id", sa.Uuid(), nullable=False),
        sa.Column("sale_number", sa.String(length=16), nullable=False),
        sa.Column("reported_by", sa.Uuid(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("owner_reply", sa.String(length=500), nullable=True),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replied_by", sa.Uuid(), nullable=True),
        sa.CheckConstraint("version >= 1", name=op.f("sale_error_report_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("sale_error_report_pkey")),
    )
    op.create_index(
        "sale_error_report_sale_idx", "sale_error_report", ["shop_id", "sale_id"], unique=False
    )
    op.create_table(
        "sale_line",
        sa.Column("sale_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("article_name_snapshot", sa.String(length=250), nullable=False),
        sa.Column("sale_mode", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=1), nullable=False),
        sa.Column("stock_unit", sa.String(length=8), nullable=False),
        sa.Column("stock_qty", sa.Numeric(precision=12, scale=1), nullable=False),
        sa.Column("base_price_snapshot", sa.BigInteger(), nullable=True),
        sa.Column("unit_price", sa.BigInteger(), nullable=False),
        sa.Column("line_total", sa.BigInteger(), nullable=False),
        sa.Column("frozen_last_cost", sa.BigInteger(), nullable=True),
        sa.Column("frozen_wac", sa.BigInteger(), nullable=True),
        sa.Column("margin", sa.BigInteger(), nullable=True),
        sa.Column("margin_wac", sa.BigInteger(), nullable=True),
        sa.CheckConstraint("quantity > 0", name=op.f("sale_line_quantity_positive_check")),
        sa.CheckConstraint("unit_price >= 0", name=op.f("sale_line_unit_price_non_negative_check")),
        sa.PrimaryKeyConstraint("sale_id", "position", name=op.f("sale_line_pkey")),
    )
    op.create_index("sale_line_article_idx", "sale_line", ["shop_id", "article_id"], unique=False)
    op.create_table(
        "sale_payment",
        sa.Column("sale_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("mode_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=True),
        sa.Column("nature", sa.String(length=16), nullable=False),
        sa.CheckConstraint("amount > 0", name=op.f("sale_payment_amount_positive_check")),
        sa.PrimaryKeyConstraint("sale_id", "position", name=op.f("sale_payment_pkey")),
    )
    op.create_index("sale_payment_mode_idx", "sale_payment", ["shop_id", "mode_id"], unique=False)
    op.create_table(
        "sold_chassis",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("chassis_key", sa.String(length=64), nullable=False),
        sa.Column("chassis_value", sa.String(length=64), nullable=False),
        sa.Column("active_key", sa.String(length=64), nullable=True),
        sa.Column("sale_id", sa.Uuid(), nullable=False),
        sa.Column("sale_number", sa.String(length=16), nullable=False),
        sa.CheckConstraint(
            "active_key IS NULL OR active_key = chassis_key",
            name=op.f("sold_chassis_active_matches_key_check"),
        ),
        sa.CheckConstraint("version >= 1", name=op.f("sold_chassis_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("sold_chassis_pkey")),
        sa.UniqueConstraint("shop_id", "active_key", name="sold_chassis_active"),
    )
    op.create_index("sold_chassis_sale_idx", "sold_chassis", ["shop_id", "sale_id"], unique=False)
    op.create_table(
        "sold_detail",
        sa.Column("sale_id", sa.Uuid(), nullable=False),
        sa.Column("line_position", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("color", sa.String(length=64), nullable=True),
        sa.Column("chassis_number", sa.String(length=64), nullable=True),
        sa.Column("chassis_key", sa.String(length=64), nullable=True),
        sa.Column("engine_number", sa.String(length=64), nullable=True),
        sa.Column("size", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint(
            "sale_id", "line_position", "position", name=op.f("sold_detail_pkey")
        ),
    )
    op.create_index(
        "sold_detail_chassis_idx", "sold_detail", ["shop_id", "chassis_key"], unique=False
    )


def downgrade() -> None:
    op.drop_index("sold_detail_chassis_idx", table_name="sold_detail")
    op.drop_table("sold_detail")
    op.drop_index("sold_chassis_sale_idx", table_name="sold_chassis")
    op.drop_table("sold_chassis")
    op.drop_index("sale_payment_mode_idx", table_name="sale_payment")
    op.drop_table("sale_payment")
    op.drop_index("sale_line_article_idx", table_name="sale_line")
    op.drop_table("sale_line")
    op.drop_index("sale_error_report_sale_idx", table_name="sale_error_report")
    op.drop_table("sale_error_report")
    op.drop_index("sale_shop_seller_idx", table_name="sale")
    op.drop_index("sale_shop_provisional_idx", table_name="sale")
    op.drop_index("sale_shop_date_idx", table_name="sale")
    op.drop_index("sale_shop_customer_idx", table_name="sale")
    op.drop_index("sale_shop_cancelled_idx", table_name="sale")
    op.drop_table("sale")
    op.drop_table("receipt_print")
    op.drop_index("customer_shop_sort_idx", table_name="customer")
    op.drop_table("customer")
