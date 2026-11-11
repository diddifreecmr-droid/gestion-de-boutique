"""Synchronisation hors connexion : traces des opérations reçues (T23, specs § 6.5).

Révision : 0013_sync
Précédente : 0012_min_price_rules
Créée le : 2026-11-11

- `sync_operation` : une ligne par `op_id` (idempotence de `POST /sync`, TR-11), résultat
  gardé (`accepted` + numéro définitif, ou `rejected` + code et motif), numéro provisoire
  indexé par boutique (RG-T06). Table vide en V1 : le droit `offline_capture` est faux.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013_sync"
down_revision: str | None = "0012_min_price_rules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "sync_operation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("op_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provisional_number", sa.String(length=32), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("captured_at", _TS, nullable=False),
        sa.Column("received_at", _TS, nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("number", sa.String(length=16), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.CheckConstraint("version >= 1", name=op.f("sync_operation_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("sync_operation_pkey")),
    )
    op.create_index(
        "sync_operation_shop_provisional_idx",
        "sync_operation",
        ["shop_id", "provisional_number"],
    )


def downgrade() -> None:
    op.drop_index("sync_operation_shop_provisional_idx", table_name="sync_operation")
    op.drop_table("sync_operation")
