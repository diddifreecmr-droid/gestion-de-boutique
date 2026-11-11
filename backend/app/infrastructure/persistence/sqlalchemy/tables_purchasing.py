"""Tables du module Achats (T15, specs § 5.3) : fournisseurs, achats, lignes, frais, paiements.

- `supplier` : nom unique sans casse par boutique (`supplier_name` sur `name_key`).
- `purchase` : numéro unique (`purchase_number`) ; `purchase_date` indexée (UC-ACH-05) ;
  `entry_at` = date d'opération de ses entrées de stock (ordre des listes) ; totaux recopiés
  pour les rapports (la vérité reste les lignes et les frais).
- `purchase_line`, `purchase_fee`, `supplier_payment` : enfants **réécrits** avec l'achat (il
  est enregistré d'un bloc ; le verrou optimiste de la ligne mère les protège). Les lignes
  gardent leur chiffrage (quantité de stock, total, part des frais, coût unitaire final).
- Aucune clé étrangère (intégrité garantie par l'application, comme pour le socle).
"""

import sqlalchemy as sa

from app.infrastructure.persistence.sqlalchemy.schema import metadata

_TS = sa.DateTime(timezone=True)
_QTY = sa.Numeric(12, 1)

supplier = sa.Table(
    "supplier",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.Column("name", sa.String(120), nullable=False),
    sa.Column("name_key", sa.String(120), nullable=False),
    sa.Column("phone", sa.String(120), nullable=True),
    sa.Column("city", sa.String(120), nullable=True),
    sa.Column("country", sa.String(120), nullable=True),
    sa.Column("note", sa.String(500), nullable=True),
    sa.Column("active", sa.Boolean, nullable=False),
    sa.Column("created_at", _TS, nullable=False),
    sa.UniqueConstraint("shop_id", "name_key", name="supplier_name"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
)

purchase = sa.Table(
    "purchase",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.Column("number", sa.String(16), nullable=False),
    sa.Column("supplier_id", sa.Uuid, nullable=True),
    sa.Column("purchase_date", sa.Date, nullable=False),
    sa.Column("entry_at", _TS, nullable=False),
    sa.Column("location_id", sa.Uuid, nullable=False),
    sa.Column("invoice_ref", sa.String(64), nullable=True),
    sa.Column("invoice_photo_id", sa.Uuid, nullable=True),
    sa.Column("note", sa.String(500), nullable=True),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("merchandise_total", sa.BigInteger, nullable=False),
    sa.Column("fees_total", sa.BigInteger, nullable=False),
    sa.Column("total", sa.BigInteger, nullable=False),
    sa.Column("created_by", sa.Uuid, nullable=False),
    sa.Column("device_id", sa.Uuid, nullable=False),
    sa.Column("captured_at", _TS, nullable=False),
    sa.Column("received_at", _TS, nullable=False),
    sa.Column("cancelled_at", _TS, nullable=True),
    sa.Column("cancelled_by", sa.Uuid, nullable=True),
    sa.Column("cancel_reason", sa.String(500), nullable=True),
    sa.UniqueConstraint("shop_id", "number", name="purchase_number"),
    sa.Index("purchase_shop_date_idx", "shop_id", "purchase_date"),
    sa.Index("purchase_shop_supplier_idx", "shop_id", "supplier_id"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
    sa.CheckConstraint("total >= 0", name="total_non_negative"),
)

purchase_line = sa.Table(
    "purchase_line",
    metadata,
    sa.Column("purchase_id", sa.Uuid, nullable=False),
    sa.Column("position", sa.Integer, nullable=False),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("article_id", sa.Uuid, nullable=False),
    sa.Column("entered_qty", _QTY, nullable=False),
    sa.Column("entered_unit", sa.String(8), nullable=False),
    sa.Column("stock_unit", sa.String(8), nullable=False),
    sa.Column("stock_qty", _QTY, nullable=False),
    sa.Column("unit_price", sa.BigInteger, nullable=False),
    sa.Column("line_total", sa.BigInteger, nullable=False),
    sa.Column("fee_share", sa.BigInteger, nullable=False),
    sa.Column("final_unit_cost", sa.BigInteger, nullable=False),
    sa.PrimaryKeyConstraint("purchase_id", "position"),
    sa.Index("purchase_line_article_idx", "shop_id", "article_id"),
    sa.CheckConstraint("entered_qty > 0", name="entered_qty_positive"),
    sa.CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
)

purchase_fee = sa.Table(
    "purchase_fee",
    metadata,
    sa.Column("purchase_id", sa.Uuid, nullable=False),
    sa.Column("position", sa.Integer, nullable=False),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("kind", sa.String(16), nullable=False),
    sa.Column("label", sa.String(120), nullable=True),
    sa.Column("amount", sa.BigInteger, nullable=False),
    sa.PrimaryKeyConstraint("purchase_id", "position"),
    sa.CheckConstraint("amount >= 0", name="amount_non_negative"),
)

supplier_payment = sa.Table(
    "supplier_payment",
    metadata,
    sa.Column("id", sa.Uuid, nullable=False),
    sa.Column("purchase_id", sa.Uuid, nullable=False),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("position", sa.Integer, nullable=False),
    sa.Column("paid_on", sa.Date, nullable=False),
    sa.Column("amount", sa.BigInteger, nullable=False),
    sa.Column("mode_id", sa.Uuid, nullable=False),
    sa.Column("reference", sa.String(64), nullable=True),
    sa.Column("recorded_at", _TS, nullable=False),
    sa.Column("recorded_by", sa.Uuid, nullable=False),
    sa.PrimaryKeyConstraint("purchase_id", "position"),
    sa.Index("supplier_payment_purchase_idx", "shop_id", "purchase_id"),
    sa.CheckConstraint("amount > 0", name="amount_positive"),
)
