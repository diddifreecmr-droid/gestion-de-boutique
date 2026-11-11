"""Tables du module Dépenses (T18, migration `0004_expenses`) — specs § 5.5.

- `expense` : numéro unique par boutique (`expense_number`, = `UniqueKey` du port), montant
  `BIGINT > 0` (TR-06), capture (`created_by`, `device_id`, `captured_at`, `received_at`,
  RG-T04) et annulation (`cancelled_at/by`, `cancel_reason`, TR-08). Index `(shop_id,
  spent_on)` pour les périodes, `(shop_id, received_at, id)` pour la pagination.
- `tag` : nom unique **sans casse** par la colonne `name_key` calculée en Python (NFC +
  `casefold`, portable : aucune collation ni `lower()` propre à un moteur) ; `merged_into`.
  `name_key` est plus large que `name` : `casefold` peut allonger (« ß » → « ss »).
- `expense_tag` : association dépense ↔ tag (`shop_id` en tête de l'index des filtres).

Aucune clé étrangère, comme pour le socle : l'intégrité référentielle est garantie par
l'application (catégorie, mode, lieu et tags lus dans la boutique avant l'écriture).
La colonne `expense_category.requires_description` (« Autre ») est déclarée dans
`tables_shops.py` et ajoutée par la même migration.
"""

import sqlalchemy as sa

from app.infrastructure.persistence.sqlalchemy.schema import metadata

_TS = sa.DateTime(timezone=True)

expense = sa.Table(
    "expense",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.Column("number", sa.String(16), nullable=False),
    sa.Column("spent_on", sa.Date, nullable=False),
    sa.Column("amount", sa.BigInteger, nullable=False),
    sa.Column("category_id", sa.Uuid, nullable=False),
    sa.Column("payment_mode_id", sa.Uuid, nullable=False),
    sa.Column("description", sa.String(500), nullable=True),
    sa.Column("location_id", sa.Uuid, nullable=True),
    sa.Column("beneficiary", sa.String(120), nullable=True),
    sa.Column("attachment_id", sa.Uuid, nullable=True),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("created_by", sa.Uuid, nullable=False),
    sa.Column("device_id", sa.Uuid, nullable=False),
    sa.Column("captured_at", _TS, nullable=False),
    sa.Column("received_at", _TS, nullable=False),
    sa.Column("cancelled_at", _TS, nullable=True),
    sa.Column("cancelled_by", sa.Uuid, nullable=True),
    sa.Column("cancel_reason", sa.String(500), nullable=True),
    sa.UniqueConstraint("shop_id", "number", name="expense_number"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
    sa.CheckConstraint("amount > 0", name="amount_positive"),
    sa.Index("expense_shop_spent_on_idx", "shop_id", "spent_on"),
    sa.Index("expense_shop_cancelled_idx", "shop_id", "cancelled_at"),
    sa.Index("expense_shop_received_idx", "shop_id", "received_at", "id"),
)

tag = sa.Table(
    "tag",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.Column("name", sa.String(40), nullable=False),
    sa.Column("name_key", sa.String(80), nullable=False),
    sa.Column("merged_into", sa.Uuid, nullable=True),
    sa.UniqueConstraint("shop_id", "name_key", name="tag_name"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
)

expense_tag = sa.Table(
    "expense_tag",
    metadata,
    sa.Column("expense_id", sa.Uuid, nullable=False),
    sa.Column("tag_id", sa.Uuid, nullable=False),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("position", sa.Integer, nullable=False),
    sa.PrimaryKeyConstraint("expense_id", "tag_id"),
    sa.Index("expense_tag_shop_tag_idx", "shop_id", "tag_id"),
)
"""`position` garde l'ordre de saisie des tags d'une dépense."""
