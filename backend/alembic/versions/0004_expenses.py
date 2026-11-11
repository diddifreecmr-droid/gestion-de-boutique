"""Module Dépenses (T18).

Révision : 0004_expenses
Précédente : 0003
Créée le : 2026-11-11

- `expense` (numéro unique par boutique, montant > 0, capture, annulation), `tag` (nom unique
  sans casse par `name_key`, `merged_into`), `expense_tag` (association) ;
- `expense_category.requires_description` (« Autre » exige une description, UC-DEP-01),
  renseignée pour la catégorie de base « Autre » des boutiques déjà ouvertes.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_expenses"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "expense",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("number", sa.String(length=16), nullable=False),
        sa.Column("spent_on", sa.Date(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("payment_mode_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("location_id", sa.Uuid(), nullable=True),
        sa.Column("beneficiary", sa.String(length=120), nullable=True),
        sa.Column("attachment_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("captured_at", _TS, nullable=False),
        sa.Column("received_at", _TS, nullable=False),
        sa.Column("cancelled_at", _TS, nullable=True),
        sa.Column("cancelled_by", sa.Uuid(), nullable=True),
        sa.Column("cancel_reason", sa.String(length=500), nullable=True),
        sa.CheckConstraint("amount > 0", name=op.f("expense_amount_positive_check")),
        sa.CheckConstraint("version >= 1", name=op.f("expense_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("expense_pkey")),
        sa.UniqueConstraint("shop_id", "number", name="expense_number"),
    )
    op.create_index("expense_shop_spent_on_idx", "expense", ["shop_id", "spent_on"])
    op.create_index("expense_shop_received_idx", "expense", ["shop_id", "received_at", "id"])
    op.create_table(
        "tag",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("name_key", sa.String(length=80), nullable=False),
        sa.Column("merged_into", sa.Uuid(), nullable=True),
        sa.CheckConstraint("version >= 1", name=op.f("tag_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("tag_pkey")),
        sa.UniqueConstraint("shop_id", "name_key", name="tag_name"),
    )
    op.create_table(
        "expense_tag",
        sa.Column("expense_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("expense_id", "tag_id", name=op.f("expense_tag_pkey")),
    )
    op.create_index("expense_tag_shop_tag_idx", "expense_tag", ["shop_id", "tag_id"])
    with op.batch_alter_table("expense_category") as batch:
        batch.add_column(
            sa.Column(
                "requires_description", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
    category = sa.table(
        "expense_category",
        sa.column("is_base", sa.Boolean()),
        sa.column("name_key", sa.String()),
        sa.column("requires_description", sa.Boolean()),
    )
    op.execute(
        category.update()
        .where(category.c.is_base == sa.true(), category.c.name_key == "autre")
        .values(requires_description=sa.true())
    )


def downgrade() -> None:
    with op.batch_alter_table("expense_category") as batch:
        batch.drop_column("requires_description")
    op.drop_index("expense_tag_shop_tag_idx", table_name="expense_tag")
    op.drop_table("expense_tag")
    op.drop_table("tag")
    op.drop_index("expense_shop_received_idx", table_name="expense")
    op.drop_index("expense_shop_spent_on_idx", table_name="expense")
    op.drop_table("expense")
