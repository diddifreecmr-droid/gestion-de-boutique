"""Ventes : demandes de prix sous le minimum et retours / échanges (T16b).

Révision : 0010_sales_returns (après 0008_sales ; 0009_receivables, T17, est une tête parallèle
à linéariser par l'orchestrateur)
Précédente : 0009_receivables
Créée le : 2026-11-11

- `price_request` : demande d'un vendeur, statut, échéance (30 min), décision, vente liée ;
- `sale_return` : retour ou échange, lignes rendues en JSON, totaux, remboursement, baisse de
  créance, nouvelle vente d'un échange, jour du retour.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_sales_returns"
down_revision: str | None = "0009_receivables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "price_request",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("seller_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("article_name", sa.String(length=250), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("requested_price", sa.BigInteger(), nullable=False),
        sa.Column("min_price", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("requested_at", _TS, nullable=False),
        sa.Column("expires_at", _TS, nullable=False),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.Column("decided_at", _TS, nullable=True),
        sa.Column("sale_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "requested_price < min_price", name=op.f("price_request_requested_below_minimum_check")
        ),
        sa.CheckConstraint(
            "requested_price >= 0", name=op.f("price_request_requested_price_non_negative_check")
        ),
        sa.CheckConstraint("version >= 1", name=op.f("price_request_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("price_request_pkey")),
    )
    op.create_index(
        "price_request_seller_idx",
        "price_request",
        ["shop_id", "seller_id", "requested_at"],
        unique=False,
    )
    op.create_index(
        "price_request_status_idx",
        "price_request",
        ["shop_id", "status", "expires_at"],
        unique=False,
    )
    op.create_table(
        "sale_return",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("sale_id", sa.Uuid(), nullable=False),
        sa.Column("sale_number", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("lines", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("margin", sa.BigInteger(), nullable=True),
        sa.Column("margin_wac", sa.BigInteger(), nullable=True),
        sa.Column("refund_amount", sa.BigInteger(), nullable=True),
        sa.Column("refund_mode_id", sa.Uuid(), nullable=True),
        sa.Column("refunded_on", sa.Date(), nullable=True),
        sa.Column("credit_reduction", sa.BigInteger(), nullable=False),
        sa.Column("exchange_sale_id", sa.Uuid(), nullable=True),
        sa.Column("returned_at", _TS, nullable=False),
        sa.Column("returned_on", sa.Date(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "(refund_amount IS NULL) = (refund_mode_id IS NULL)",
            name=op.f("sale_return_refund_complete_check"),
        ),
        sa.CheckConstraint("amount >= 0", name=op.f("sale_return_amount_non_negative_check")),
        sa.CheckConstraint(
            "credit_reduction >= 0",
            name=op.f("sale_return_credit_reduction_non_negative_check"),
        ),
        sa.CheckConstraint("version >= 1", name=op.f("sale_return_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("sale_return_pkey")),
    )
    op.create_index("sale_return_day_idx", "sale_return", ["shop_id", "returned_on"], unique=False)
    op.create_index("sale_return_sale_idx", "sale_return", ["shop_id", "sale_id"], unique=False)


def downgrade() -> None:
    op.drop_index("sale_return_sale_idx", table_name="sale_return")
    op.drop_index("sale_return_day_idx", table_name="sale_return")
    op.drop_table("sale_return")
    op.drop_index("price_request_status_idx", table_name="price_request")
    op.drop_index("price_request_seller_idx", table_name="price_request")
    op.drop_table("price_request")
