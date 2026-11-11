"""Tables du module Créances (T17, specs § 5.4) : créances, versements, rappels, garants.

- `receivable` : une créance par vente (`receivable_sale` sur `(shop_id, sale_id)`, nul pour
  une créance ancienne) ; `status` est **recopié** du domaine à chaque écriture (filtres et
  rapports) — la vérité reste les versements (total versé et reste calculés, § 5.4) ;
  pièces jointes = liste JSON d'identifiants (le module des pièces jointes viendra plus tard).
- `installment` : numéro `R-…` unique par boutique (`installment_number`) ; `receivable_reminder`,
  `guarantor` : enfants **réécrits** avec la créance (verrou optimiste de la ligne mère).
- Aucune clé étrangère (intégrité garantie par l'application, comme pour le socle).
"""

import sqlalchemy as sa

from app.infrastructure.persistence.sqlalchemy.schema import metadata

_TS = sa.DateTime(timezone=True)

receivable = sa.Table(
    "receivable",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.Column("customer_id", sa.Uuid, nullable=False),
    sa.Column("origin", sa.String(16), nullable=False),
    sa.Column("sale_id", sa.Uuid, nullable=True),
    sa.Column("sale_number", sa.String(16), nullable=True),
    sa.Column("sale_total", sa.BigInteger, nullable=True),
    sa.Column("paid_at_sale", sa.BigInteger, nullable=False),
    sa.Column("description", sa.String(500), nullable=True),
    sa.Column("initial_amount", sa.BigInteger, nullable=False),
    sa.Column("opened_on", sa.Date, nullable=False),
    sa.Column("responsible_seller_id", sa.Uuid, nullable=True),
    sa.Column("terms", sa.String(500), nullable=True),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("attachment_ids", sa.JSON, nullable=False),
    sa.Column("written_off_on", sa.Date, nullable=True),
    sa.Column("write_off_reason", sa.String(500), nullable=True),
    sa.Column("written_off_by", sa.Uuid, nullable=True),
    sa.Column("written_off_at", _TS, nullable=True),
    sa.Column("sale_cancelled_on", sa.Date, nullable=True),
    sa.Column("sale_cancelled_at", _TS, nullable=True),
    sa.Column("recorded_at", _TS, nullable=False),
    sa.UniqueConstraint("shop_id", "sale_id", name="receivable_sale"),
    sa.Index("receivable_shop_customer_idx", "shop_id", "customer_id"),
    sa.Index("receivable_shop_responsible_idx", "shop_id", "responsible_seller_id"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
    sa.CheckConstraint("initial_amount >= 0", name="initial_non_negative"),
)

installment = sa.Table(
    "installment",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("receivable_id", sa.Uuid, nullable=False),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("position", sa.Integer, nullable=False),
    sa.Column("number", sa.String(16), nullable=False),
    sa.Column("paid_on", sa.Date, nullable=False),
    sa.Column("amount", sa.BigInteger, nullable=False),
    sa.Column("mode_id", sa.Uuid, nullable=False),
    sa.Column("reference", sa.String(64), nullable=True),
    sa.Column("nature", sa.String(16), nullable=False),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("to_refund", sa.Boolean, nullable=False),
    sa.Column("created_by", sa.Uuid, nullable=False),
    sa.Column("device_id", sa.Uuid, nullable=False),
    sa.Column("captured_at", _TS, nullable=False),
    sa.Column("received_at", _TS, nullable=False),
    sa.Column("cancelled_at", _TS, nullable=True),
    sa.Column("cancelled_by", sa.Uuid, nullable=True),
    sa.Column("cancel_reason", sa.String(500), nullable=True),
    sa.UniqueConstraint("shop_id", "number", name="installment_number"),
    sa.Index("installment_receivable_idx", "shop_id", "receivable_id"),
    sa.Index("installment_shop_paid_on_idx", "shop_id", "paid_on"),
    sa.Index("installment_shop_cancelled_idx", "shop_id", "cancelled_at"),
    sa.CheckConstraint("amount > 0", name="amount_positive"),
)

receivable_reminder = sa.Table(
    "receivable_reminder",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("receivable_id", sa.Uuid, nullable=False),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("position", sa.Integer, nullable=False),
    sa.Column("remind_on", sa.Date, nullable=False),
    sa.Column("note", sa.String(500), nullable=True),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("alerted_for", sa.Date, nullable=True),
    sa.Column("created_by", sa.Uuid, nullable=False),
    sa.Column("created_at", _TS, nullable=False),
    sa.Index("receivable_reminder_receivable_idx", "shop_id", "receivable_id"),
    sa.Index("receivable_reminder_due_idx", "shop_id", "status", "remind_on"),
)

guarantor = sa.Table(
    "guarantor",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("receivable_id", sa.Uuid, nullable=False),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("position", sa.Integer, nullable=False),
    sa.Column("name", sa.String(120), nullable=False),
    sa.Column("phone", sa.String(32), nullable=False),
    sa.Column("relation", sa.String(200), nullable=True),
    sa.Column("id_doc_type", sa.String(32), nullable=True),
    sa.Column("id_doc_number", sa.String(200), nullable=True),
    sa.Column("id_doc_photo_id", sa.Uuid, nullable=True),
    sa.Column("added_by", sa.Uuid, nullable=False),
    sa.Column("added_at", _TS, nullable=False),
    sa.Index("guarantor_receivable_idx", "shop_id", "receivable_id"),
)
