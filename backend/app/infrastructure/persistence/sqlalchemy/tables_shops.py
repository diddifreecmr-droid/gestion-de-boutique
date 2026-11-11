"""Tables du socle des boutiques (T10) : `shop_id` en tête, `version`, unicités nommées.

Les noms des contraintes `UNIQUE` sont ceux des `UniqueKey` des ports
(`application/shops/ports.py`). Les noms de lieu, de mode de paiement et de catégorie sont
uniques **sans casse** : la colonne `name_key` (nom nettoyé, `casefold`) porte la contrainte.
`shop.shop_id` vaut `shop.id` (la boutique est son propre locataire, `CHECK`). Aucune clé
étrangère : l'intégrité référentielle est garantie par l'application, comme pour le journal.
"""

from typing import Any

import sqlalchemy as sa

from app.infrastructure.persistence.sqlalchemy.schema import metadata

_TS = sa.DateTime(timezone=True)
_VERSION_CHECK = "version >= 1"


def _base(name: str, *extra: Any) -> sa.Table:
    return sa.Table(
        name,
        metadata,
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("shop_id", sa.Uuid, nullable=False),
        sa.Column("version", sa.BigInteger, nullable=False),
        *extra,
        sa.CheckConstraint(_VERSION_CHECK, name="version_positive"),
    )


shop = _base(
    "shop",
    sa.Column("account_id", sa.Uuid, nullable=False),
    sa.Column("name", sa.String(120), nullable=False),
    sa.Column("profile_code", sa.String(32), nullable=False),
    sa.Column("city", sa.String(120), nullable=False),
    sa.Column("phone", sa.String(16), nullable=False),
    sa.Column("address", sa.String(200), nullable=True),
    sa.Column("niu", sa.String(32), nullable=True),
    sa.Column("rccm", sa.String(32), nullable=True),
    sa.Column("enabled_modules", sa.JSON, nullable=False),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("created_at", _TS, nullable=False),
    sa.CheckConstraint("shop_id = id", name="own_tenant"),
)

shop_settings = _base(
    "shop_settings",
    sa.Column("receipt_format", sa.String(8), nullable=False),
    sa.Column("paper_width_mm", sa.Integer, nullable=False),
    sa.Column("printable_width_mm", sa.Integer, nullable=False),
    sa.Column("margin_mm", sa.Integer, nullable=False),
    sa.Column("font_size_pt", sa.Integer, nullable=False),
    sa.Column("show_logo", sa.Boolean, nullable=False),
    sa.Column("footer_message", sa.String(200), nullable=True),
    sa.Column("copies", sa.Integer, nullable=False),
    sa.Column("low_stock_threshold", sa.Numeric(12, 1), nullable=False),
    sa.Column("min_price_enabled", sa.Boolean, nullable=False),
    sa.Column("min_price_requires_approval", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("exchange_days", sa.Integer, nullable=True),
    sa.Column("truck_silent_hours", sa.Integer, nullable=True),
    sa.Column("transfer_in_transit_days", sa.Integer, nullable=True),
    sa.Column("reception_location_id", sa.Uuid, nullable=True),
    sa.UniqueConstraint("shop_id", name="shop_settings_shop"),
    sa.CheckConstraint("copies BETWEEN 1 AND 3", name="copies_range"),
)

location = _base(
    "location",
    sa.Column("name", sa.String(120), nullable=False),
    sa.Column("name_key", sa.String(120), nullable=False),
    sa.Column("kind", sa.String(16), nullable=False),
    sa.Column("is_point_of_sale", sa.Boolean, nullable=False),
    sa.Column("city", sa.String(200), nullable=True),
    sa.Column("display_order", sa.Integer, nullable=False),
    sa.Column("active", sa.Boolean, nullable=False),
    sa.UniqueConstraint("shop_id", "name_key", name="location_name"),
)

payment_mode = _base(
    "payment_mode",
    sa.Column("name", sa.String(60), nullable=False),
    sa.Column("name_key", sa.String(60), nullable=False),
    sa.Column("reference_required", sa.Boolean, nullable=False),
    sa.Column("active", sa.Boolean, nullable=False),
    sa.Column("display_order", sa.Integer, nullable=False),
    sa.UniqueConstraint("shop_id", "name_key", name="payment_mode_name"),
)

expense_category = _base(
    "expense_category",
    sa.Column("name", sa.String(60), nullable=False),
    sa.Column("name_key", sa.String(60), nullable=False),
    sa.Column("is_base", sa.Boolean, nullable=False),
    sa.Column("active", sa.Boolean, nullable=False),
    sa.Column("display_order", sa.Integer, nullable=False),
    # T18 (migration 0004_expenses) : « Autre » exige une description (UC-DEP-01).
    sa.Column("requires_description", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.UniqueConstraint("shop_id", "name_key", name="expense_category_name"),
)

membership = _base(
    "membership",
    sa.Column("user_id", sa.Uuid, nullable=False),
    sa.Column("role", sa.String(16), nullable=False),
    sa.Column("default_location_id", sa.Uuid, nullable=True),
    sa.Column("active", sa.Boolean, nullable=False),
    sa.UniqueConstraint("shop_id", "user_id", name="membership_user"),
    sa.Index("membership_user_idx", "user_id"),
)
"""`membership_user_idx` : rôles d'un utilisateur dans toutes ses boutiques (chaque requête)."""

admin_access_grant = _base(
    "admin_access_grant",
    sa.Column("granted_by", sa.Uuid, nullable=False),
    sa.Column("granted_at", _TS, nullable=False),
    sa.Column("expires_at", _TS, nullable=False),
    sa.Column("revoked_at", _TS, nullable=True),
    sa.Column("revoked_by", sa.Uuid, nullable=True),
    sa.Index("admin_access_grant_shop_expires_idx", "shop_id", "expires_at"),
)
