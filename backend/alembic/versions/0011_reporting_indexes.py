"""Tableau de bord : index de période manquants pour les agrégats du jour (T19, specs § 10).

Révision : 0011_reporting_indexes
Précédente : 0010_sales_returns
Créée le : 2026-11-11

Les agrégats § 14.1 rattachent une annulation au jour où elle est faite (Q-09) et un
remboursement à sa date : sans ces index, ces requêtes balaieraient toute la table.

- `expense (shop_id, cancelled_at)` : dépenses annulées pendant la période ;
- `installment (shop_id, cancelled_at)` : versements annulés pendant la période ;
- `sale_return (shop_id, refunded_on)` : remboursements de la période.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0011_reporting_indexes"
down_revision: str | None = "0010_sales_returns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEXES = (
    ("expense_shop_cancelled_idx", "expense", ["shop_id", "cancelled_at"]),
    ("installment_shop_cancelled_idx", "installment", ["shop_id", "cancelled_at"]),
    ("sale_return_refund_day_idx", "sale_return", ["shop_id", "refunded_on"]),
)


def upgrade() -> None:
    for name, table, columns in _INDEXES:
        op.create_index(name, table, columns, unique=False)


def downgrade() -> None:
    for name, table, _columns in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
