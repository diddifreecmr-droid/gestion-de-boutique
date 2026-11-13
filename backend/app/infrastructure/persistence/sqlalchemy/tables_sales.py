"""Tables du module Ventes (T16a, specs § 5.4) : clients, ventes, lignes, détails, paiements,
réservations de châssis, signalements, impressions de reçus.

- `customer` : téléphone E.164 unique par boutique (`customer_phone`, sur `phone_key` : copie du
  téléphone, `NULL` une fois le client désactivé par l'annulation de son import — QC-6,
  migration 0020) ; `search_key` (nom plié + chiffres du téléphone) et `sort_key` calculés par
  le domaine (recherche portable).
- `sale` : numéro unique (`sale_number`) ; totaux recopiés pour les rapports (la vérité reste
  les lignes et les paiements) ; `sold_at` = instant de la vente (ordre des listes).
- `sale_line`, `sold_detail`, `sale_payment` : enfants **réécrits** avec la vente (verrou
  optimiste de la ligne mère). La ligne garde ses instantanés, ses **coûts figés** et ses
  marges calculées (`NULL` = non calculable, RG-T15) ; `sold_detail.chassis_key` sert la
  recherche par châssis (RG-M02).
- `sold_chassis` : unicité « châssis d'une vente non annulée » (RG-M01) par `active_key`
  (`NULL` une fois libéré) — même procédé portable que `alert_active_dedup`.
- Aucune clé étrangère (intégrité garantie par l'application, comme pour le socle).
"""

import sqlalchemy as sa

from app.infrastructure.persistence.sqlalchemy.schema import metadata

_TS = sa.DateTime(timezone=True)
_QTY = sa.Numeric(12, 1)


def _identity() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("shop_id", sa.Uuid, nullable=False),
        sa.Column("version", sa.BigInteger, nullable=False),
    ]


customer = sa.Table(
    "customer",
    metadata,
    *_identity(),
    sa.Column("name", sa.String(120), nullable=False),
    sa.Column("phone", sa.String(16), nullable=False),
    sa.Column("phone_key", sa.String(16), nullable=True),
    sa.Column("kind", sa.String(16), nullable=False),
    sa.Column("city", sa.String(200), nullable=True),
    sa.Column("address", sa.String(200), nullable=True),
    sa.Column("id_doc_type", sa.String(32), nullable=True),
    sa.Column("id_doc_number", sa.String(200), nullable=True),
    sa.Column("id_doc_photo_id", sa.Uuid, nullable=True),
    sa.Column("credit_limit", sa.BigInteger, nullable=True),
    sa.Column("note", sa.String(500), nullable=True),
    sa.Column("search_key", sa.String(250), nullable=False),
    sa.Column("sort_key", sa.String(250), nullable=False),
    sa.Column("created_by", sa.Uuid, nullable=False),
    sa.Column("created_at", _TS, nullable=False),
    sa.UniqueConstraint("shop_id", "phone_key", name="customer_phone"),
    sa.Index("customer_shop_sort_idx", "shop_id", "sort_key"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
    sa.CheckConstraint("credit_limit >= 0", name="credit_limit_non_negative"),
)

sale = sa.Table(
    "sale",
    metadata,
    *_identity(),
    sa.Column("number", sa.String(16), nullable=False),
    sa.Column("provisional_number", sa.String(32), nullable=True),
    sa.Column("kind", sa.String(8), nullable=False),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("location_id", sa.Uuid, nullable=False),
    sa.Column("seller_id", sa.Uuid, nullable=False),
    sa.Column("customer_id", sa.Uuid, nullable=True),
    sa.Column("sold_on", sa.Date, nullable=False),
    sa.Column("sold_at", _TS, nullable=False),
    sa.Column("total", sa.BigInteger, nullable=False),
    sa.Column("paid", sa.BigInteger, nullable=False),
    sa.Column("note", sa.String(500), nullable=True),
    sa.Column("reminder_on", sa.Date, nullable=True),
    sa.Column("credit_terms", sa.String(500), nullable=True),
    sa.Column("stock_to_verify", sa.Boolean, nullable=False),
    sa.Column("created_by", sa.Uuid, nullable=False),
    sa.Column("device_id", sa.Uuid, nullable=False),
    sa.Column("captured_at", _TS, nullable=False),
    sa.Column("received_at", _TS, nullable=False),
    sa.Column("cancelled_at", _TS, nullable=True),
    sa.Column("cancelled_by", sa.Uuid, nullable=True),
    sa.Column("cancel_reason", sa.String(500), nullable=True),
    sa.UniqueConstraint("shop_id", "number", name="sale_number"),
    sa.Index("sale_shop_date_idx", "shop_id", "sold_on"),
    sa.Index("sale_shop_seller_idx", "shop_id", "seller_id", "sold_on"),
    sa.Index("sale_shop_customer_idx", "shop_id", "customer_id"),
    sa.Index("sale_shop_cancelled_idx", "shop_id", "cancelled_at"),
    sa.Index("sale_shop_provisional_idx", "shop_id", "provisional_number"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
    sa.CheckConstraint("paid >= 0 AND paid <= total", name="paid_within_total"),
)

sale_line = sa.Table(
    "sale_line",
    metadata,
    sa.Column("sale_id", sa.Uuid, nullable=False),
    sa.Column("position", sa.Integer, nullable=False),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("article_id", sa.Uuid, nullable=False),
    sa.Column("article_name_snapshot", sa.String(250), nullable=False),
    sa.Column("sale_mode", sa.String(8), nullable=False),
    sa.Column("quantity", _QTY, nullable=False),
    sa.Column("stock_unit", sa.String(8), nullable=False),
    sa.Column("stock_qty", _QTY, nullable=False),
    sa.Column("base_price_snapshot", sa.BigInteger, nullable=True),
    sa.Column("unit_price", sa.BigInteger, nullable=False),
    sa.Column("line_total", sa.BigInteger, nullable=False),
    sa.Column("frozen_last_cost", sa.BigInteger, nullable=True),
    sa.Column("frozen_wac", sa.BigInteger, nullable=True),
    sa.Column("margin", sa.BigInteger, nullable=True),
    sa.Column("margin_wac", sa.BigInteger, nullable=True),
    sa.PrimaryKeyConstraint("sale_id", "position"),
    sa.Index("sale_line_article_idx", "shop_id", "article_id"),
    sa.CheckConstraint("quantity > 0", name="quantity_positive"),
    sa.CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
)

sold_detail = sa.Table(
    "sold_detail",
    metadata,
    sa.Column("sale_id", sa.Uuid, nullable=False),
    sa.Column("line_position", sa.Integer, nullable=False),
    sa.Column("position", sa.Integer, nullable=False),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("color", sa.String(64), nullable=True),
    sa.Column("chassis_number", sa.String(64), nullable=True),
    sa.Column("chassis_key", sa.String(64), nullable=True),
    sa.Column("engine_number", sa.String(64), nullable=True),
    sa.Column("size", sa.String(64), nullable=True),
    sa.PrimaryKeyConstraint("sale_id", "line_position", "position"),
    sa.Index("sold_detail_chassis_idx", "shop_id", "chassis_key"),
)

sale_payment = sa.Table(
    "sale_payment",
    metadata,
    sa.Column("sale_id", sa.Uuid, nullable=False),
    sa.Column("position", sa.Integer, nullable=False),
    sa.Column("id", sa.Uuid, nullable=False),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("mode_id", sa.Uuid, nullable=False),
    sa.Column("amount", sa.BigInteger, nullable=False),
    sa.Column("reference", sa.String(64), nullable=True),
    sa.Column("nature", sa.String(16), nullable=False),
    sa.PrimaryKeyConstraint("sale_id", "position"),
    sa.Index("sale_payment_mode_idx", "shop_id", "mode_id"),
    sa.CheckConstraint("amount > 0", name="amount_positive"),
)

sold_chassis = sa.Table(
    "sold_chassis",
    metadata,
    *_identity(),
    sa.Column("chassis_key", sa.String(64), nullable=False),
    sa.Column("chassis_value", sa.String(64), nullable=False),
    sa.Column("active_key", sa.String(64), nullable=True),
    sa.Column("sale_id", sa.Uuid, nullable=False),
    sa.Column("sale_number", sa.String(16), nullable=False),
    sa.UniqueConstraint("shop_id", "active_key", name="sold_chassis_active"),
    sa.Index("sold_chassis_sale_idx", "shop_id", "sale_id"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
    sa.CheckConstraint("active_key IS NULL OR active_key = chassis_key", name="active_matches_key"),
)

sale_error_report = sa.Table(
    "sale_error_report",
    metadata,
    *_identity(),
    sa.Column("sale_id", sa.Uuid, nullable=False),
    sa.Column("sale_number", sa.String(16), nullable=False),
    sa.Column("reported_by", sa.Uuid, nullable=False),
    sa.Column("description", sa.String(500), nullable=False),
    sa.Column("reported_at", _TS, nullable=False),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("owner_reply", sa.String(500), nullable=True),
    sa.Column("replied_at", _TS, nullable=True),
    sa.Column("replied_by", sa.Uuid, nullable=True),
    sa.Index("sale_error_report_sale_idx", "shop_id", "sale_id"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
)

receipt_print = sa.Table(
    "receipt_print",
    metadata,
    *_identity(),
    sa.Column("sale_id", sa.Uuid, nullable=False),
    sa.Column("sequence", sa.Integer, nullable=False),
    sa.Column("printed_at", _TS, nullable=False),
    sa.Column("printed_by", sa.Uuid, nullable=False),
    sa.UniqueConstraint("shop_id", "sale_id", "sequence", name="receipt_print_sequence"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
    sa.CheckConstraint("sequence >= 1", name="sequence_positive"),
)
