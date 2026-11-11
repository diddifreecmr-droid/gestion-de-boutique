"""Créances et versements : créances, versements, rappels, garants (T17).

Révision : 0009_receivables (après 0008_sales ; 0010_sales_returns, T16b, est une tête
parallèle à linéariser par l'orchestrateur)
Précédente : 0008_sales
Créée le : 2026-11-11

- `receivable` : une créance par vente (`receivable_sale`), statut recopié, pièces en JSON ;
- `installment` : versements `R-…`, numéro unique par boutique (`installment_number`) ;
- `receivable_reminder`, `guarantor` : enfants réécrits avec la créance.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_receivables"
down_revision: str | None = "0008_sales"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "guarantor",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("receivable_id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("relation", sa.String(length=200), nullable=True),
        sa.Column("id_doc_type", sa.String(length=32), nullable=True),
        sa.Column("id_doc_number", sa.String(length=200), nullable=True),
        sa.Column("id_doc_photo_id", sa.Uuid(), nullable=True),
        sa.Column("added_by", sa.Uuid(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("guarantor_pkey")),
    )
    op.create_index(
        "guarantor_receivable_idx", "guarantor", ["shop_id", "receivable_id"], unique=False
    )
    op.create_table(
        "installment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("receivable_id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(length=16), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("mode_id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=True),
        sa.Column("nature", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("to_refund", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.Uuid(), nullable=True),
        sa.Column("cancel_reason", sa.String(length=500), nullable=True),
        sa.CheckConstraint("amount > 0", name=op.f("installment_amount_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("installment_pkey")),
        sa.UniqueConstraint("shop_id", "number", name="installment_number"),
    )
    op.create_index(
        "installment_receivable_idx", "installment", ["shop_id", "receivable_id"], unique=False
    )
    op.create_index(
        "installment_shop_paid_on_idx", "installment", ["shop_id", "paid_on"], unique=False
    )
    op.create_table(
        "receivable",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("sale_id", sa.Uuid(), nullable=True),
        sa.Column("sale_number", sa.String(length=16), nullable=True),
        sa.Column("sale_total", sa.BigInteger(), nullable=True),
        sa.Column("paid_at_sale", sa.BigInteger(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("initial_amount", sa.BigInteger(), nullable=False),
        sa.Column("opened_on", sa.Date(), nullable=False),
        sa.Column("responsible_seller_id", sa.Uuid(), nullable=True),
        sa.Column("terms", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attachment_ids", sa.JSON(), nullable=False),
        sa.Column("written_off_on", sa.Date(), nullable=True),
        sa.Column("write_off_reason", sa.String(length=500), nullable=True),
        sa.Column("written_off_by", sa.Uuid(), nullable=True),
        sa.Column("written_off_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sale_cancelled_on", sa.Date(), nullable=True),
        sa.Column("sale_cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "initial_amount >= 0", name=op.f("receivable_initial_non_negative_check")
        ),
        sa.CheckConstraint("version >= 1", name=op.f("receivable_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("receivable_pkey")),
        sa.UniqueConstraint("shop_id", "sale_id", name="receivable_sale"),
    )
    op.create_index(
        "receivable_shop_customer_idx", "receivable", ["shop_id", "customer_id"], unique=False
    )
    op.create_index(
        "receivable_shop_responsible_idx",
        "receivable",
        ["shop_id", "responsible_seller_id"],
        unique=False,
    )
    op.create_table(
        "receivable_reminder",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("receivable_id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("remind_on", sa.Date(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("alerted_for", sa.Date(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("receivable_reminder_pkey")),
    )
    op.create_index(
        "receivable_reminder_due_idx",
        "receivable_reminder",
        ["shop_id", "status", "remind_on"],
        unique=False,
    )
    op.create_index(
        "receivable_reminder_receivable_idx",
        "receivable_reminder",
        ["shop_id", "receivable_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("receivable_reminder_receivable_idx", table_name="receivable_reminder")
    op.drop_index("receivable_reminder_due_idx", table_name="receivable_reminder")
    op.drop_table("receivable_reminder")
    op.drop_index("receivable_shop_responsible_idx", table_name="receivable")
    op.drop_index("receivable_shop_customer_idx", table_name="receivable")
    op.drop_table("receivable")
    op.drop_index("installment_shop_paid_on_idx", table_name="installment")
    op.drop_index("installment_receivable_idx", table_name="installment")
    op.drop_table("installment")
    op.drop_index("guarantor_receivable_idx", table_name="guarantor")
    op.drop_table("guarantor")
