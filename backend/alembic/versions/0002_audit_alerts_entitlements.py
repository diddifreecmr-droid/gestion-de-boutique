"""Journal d'actions, alertes, surcharges de droits d'offre (T09).

Révision : 0002
Précédente : 0001
Créée le : 2026-11-11

- `audit_entry` : journal en ajout seul (RG-J01), index `(shop_id, received_at, id)` et
  `(shop_id, entity_type, entity_id)` ;
- `alert` : unicité portable `UNIQUE (shop_id, recipient_id, dedup_active_key)` ;
- `entitlement_override` : droits d'offre posés par l'administrateur (TR-26).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "audit_entry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("entity_number", sa.String(length=500), nullable=True),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("sensitive", sa.Boolean(), nullable=False),
        sa.Column("captured_at", _TS, nullable=False),
        sa.Column("received_at", _TS, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("audit_entry_pkey")),
    )
    op.create_index(
        "audit_entry_shop_received_idx", "audit_entry", ["shop_id", "received_at", "id"]
    )
    op.create_index(
        "audit_entry_shop_entity_idx", "audit_entry", ["shop_id", "entity_type", "entity_id"]
    )
    op.create_index(
        "audit_entry_shop_actor_idx", "audit_entry", ["shop_id", "actor_id", "received_at"]
    )
    op.create_table(
        "alert",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("entity_number", sa.String(length=500), nullable=True),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False),
        sa.Column("created_at", _TS, nullable=False),
        sa.Column("resolved_at", _TS, nullable=True),
        sa.Column("dedup_key", sa.String(length=200), nullable=True),
        sa.Column("dedup_active_key", sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("alert_pkey")),
        sa.UniqueConstraint(
            "shop_id", "recipient_id", "dedup_active_key", name=op.f("alert_active_dedup")
        ),
        sa.CheckConstraint("version >= 1", name=op.f("alert_version_positive_check")),
        sa.CheckConstraint(
            "dedup_active_key IS NULL OR dedup_active_key = dedup_key",
            name=op.f("alert_dedup_active_matches_check"),
        ),
    )
    op.create_index("alert_shop_recipient_idx", "alert", ["shop_id", "recipient_id", "created_at"])
    op.create_table(
        "entitlement_override",
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("entitlement", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("set_by", sa.Uuid(), nullable=False),
        sa.Column("set_at", _TS, nullable=False),
        sa.PrimaryKeyConstraint("shop_id", "entitlement", name=op.f("entitlement_override_pkey")),
    )


def downgrade() -> None:
    op.drop_table("entitlement_override")
    op.drop_index("alert_shop_recipient_idx", table_name="alert")
    op.drop_table("alert")
    op.drop_index("audit_entry_shop_actor_idx", table_name="audit_entry")
    op.drop_index("audit_entry_shop_entity_idx", table_name="audit_entry")
    op.drop_index("audit_entry_shop_received_idx", table_name="audit_entry")
    op.drop_table("audit_entry")
