"""Identité en base et socle des boutiques (T10).

Révision : 0003
Précédente : 0002
Créée le : 2026-11-11

- plateforme : `app_user` (téléphone unique, deux compteurs d'essais), `device_session`,
  `merchant_account` (offre, noms des boutiques du compte) ;
- boutique : `shop` (`shop_id = id`), `shop_settings` (un jeu par boutique), `location`,
  `payment_mode`, `expense_category` (noms uniques sans casse, colonne `name_key`),
  `membership` (`UNIQUE (shop_id, user_id)`, index par utilisateur), `admin_access_grant`.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_access_grant",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("granted_by", sa.Uuid(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.Uuid(), nullable=True),
        sa.CheckConstraint("version >= 1", name=op.f("admin_access_grant_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("admin_access_grant_pkey")),
    )
    op.create_index(
        "admin_access_grant_shop_expires_idx",
        "admin_access_grant",
        ["shop_id", "expires_at"],
        unique=False,
    )
    op.create_table(
        "app_user",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("phone", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("secret_hash", sa.String(length=255), nullable=False),
        sa.Column("is_platform_admin", sa.Boolean(), nullable=False),
        sa.Column("must_change_pin", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pin_change_failures", sa.Integer(), nullable=False),
        sa.Column("pin_change_locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "failed_attempts >= 0 AND pin_change_failures >= 0",
            name=op.f("app_user_failures_positive_check"),
        ),
        sa.CheckConstraint("version >= 1", name=op.f("app_user_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("app_user_pkey")),
        sa.UniqueConstraint("phone", name="user_phone"),
    )
    op.create_table(
        "device_session",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("device_label", sa.String(length=100), nullable=False),
        sa.Column("refresh_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sliding", sa.Boolean(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("version >= 1", name=op.f("device_session_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("device_session_pkey")),
    )
    op.create_index(
        "device_session_user_device_idx", "device_session", ["user_id", "device_id"], unique=False
    )
    op.create_table(
        "expense_category",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("name_key", sa.String(length=60), nullable=False),
        sa.Column("is_base", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("version >= 1", name=op.f("expense_category_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("expense_category_pkey")),
        sa.UniqueConstraint("shop_id", "name_key", name="expense_category_name"),
    )
    op.create_table(
        "location",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_key", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("is_point_of_sale", sa.Boolean(), nullable=False),
        sa.Column("city", sa.String(length=200), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("version >= 1", name=op.f("location_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("location_pkey")),
        sa.UniqueConstraint("shop_id", "name_key", name="location_name"),
    )
    op.create_table(
        "membership",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("default_location_id", sa.Uuid(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("version >= 1", name=op.f("membership_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("membership_pkey")),
        sa.UniqueConstraint("shop_id", "user_id", name="membership_user"),
    )
    op.create_index("membership_user_idx", "membership", ["user_id"], unique=False)
    op.create_table(
        "merchant_account",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=16), nullable=False),
        sa.Column("plan", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("shop_names", sa.JSON(), nullable=False),
        sa.CheckConstraint("version >= 1", name=op.f("merchant_account_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("merchant_account_pkey")),
        sa.UniqueConstraint("phone", name="merchant_account_phone"),
    )
    op.create_table(
        "payment_mode",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("name_key", sa.String(length=60), nullable=False),
        sa.Column("reference_required", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("version >= 1", name=op.f("payment_mode_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("payment_mode_pkey")),
        sa.UniqueConstraint("shop_id", "name_key", name="payment_mode_name"),
    )
    op.create_table(
        "shop",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("profile_code", sa.String(length=32), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=16), nullable=False),
        sa.Column("address", sa.String(length=200), nullable=True),
        sa.Column("niu", sa.String(length=32), nullable=True),
        sa.Column("rccm", sa.String(length=32), nullable=True),
        sa.Column("enabled_modules", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("shop_id = id", name=op.f("shop_own_tenant_check")),
        sa.CheckConstraint("version >= 1", name=op.f("shop_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("shop_pkey")),
    )
    op.create_table(
        "shop_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("receipt_format", sa.String(length=8), nullable=False),
        sa.Column("paper_width_mm", sa.Integer(), nullable=False),
        sa.Column("printable_width_mm", sa.Integer(), nullable=False),
        sa.Column("margin_mm", sa.Integer(), nullable=False),
        sa.Column("font_size_pt", sa.Integer(), nullable=False),
        sa.Column("show_logo", sa.Boolean(), nullable=False),
        sa.Column("footer_message", sa.String(length=200), nullable=True),
        sa.Column("copies", sa.Integer(), nullable=False),
        sa.Column("low_stock_threshold", sa.Numeric(precision=12, scale=1), nullable=False),
        sa.Column("min_price_enabled", sa.Boolean(), nullable=False),
        sa.Column("exchange_days", sa.Integer(), nullable=True),
        sa.Column("truck_silent_hours", sa.Integer(), nullable=True),
        sa.Column("transfer_in_transit_days", sa.Integer(), nullable=True),
        sa.Column("reception_location_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("copies BETWEEN 1 AND 3", name=op.f("shop_settings_copies_range_check")),
        sa.CheckConstraint("version >= 1", name=op.f("shop_settings_version_positive_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("shop_settings_pkey")),
        sa.UniqueConstraint("shop_id", name="shop_settings_shop"),
    )


def downgrade() -> None:
    op.drop_table("shop_settings")
    op.drop_table("shop")
    op.drop_table("payment_mode")
    op.drop_table("merchant_account")
    op.drop_index("membership_user_idx", table_name="membership")
    op.drop_table("membership")
    op.drop_table("location")
    op.drop_table("expense_category")
    op.drop_index("device_session_user_device_idx", table_name="device_session")
    op.drop_table("device_session")
    op.drop_table("app_user")
    op.drop_index("admin_access_grant_shop_expires_idx", table_name="admin_access_grant")
    op.drop_table("admin_access_grant")
