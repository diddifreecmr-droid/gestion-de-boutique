"""Tables des demandes de prix et des retours (T16b, specs § 5.4 `PRICE_REQUEST`, `SALE_RETURN`).

- `price_request` : demande d'un vendeur (article, lieu, prix demandé, minimum copié), statut
  tenu, échéance (`expires_at`), décision, vente liée (usage unique). Index vendeur (liste
  « mes demandes ») et statut + échéance (worker d'expiration, TR-19).
- `sale_return` : retour ou échange sur une vente ; lignes rendues en JSON (`lines`, schéma
  § 5.4 : ligne, article, quantités, état, montant, coûts figés, châssis) ; totaux recopiés
  pour le tableau de bord (montant, coût, marges — `NULL` = non calculable) ; remboursement
  (montant, mode, date), baisse de créance, nouvelle vente d'un échange, jour du retour
  (`returned_on`, index pour les indicateurs du jour, § 14.1).
- Aucune clé étrangère (intégrité garantie par l'application, comme pour le socle).
"""

import sqlalchemy as sa

from app.infrastructure.persistence.sqlalchemy.schema import metadata

_TS = sa.DateTime(timezone=True)


def _identity() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("shop_id", sa.Uuid, nullable=False),
        sa.Column("version", sa.BigInteger, nullable=False),
    ]


price_request = sa.Table(
    "price_request",
    metadata,
    *_identity(),
    sa.Column("seller_id", sa.Uuid, nullable=False),
    sa.Column("article_id", sa.Uuid, nullable=False),
    sa.Column("article_name", sa.String(250), nullable=False),
    sa.Column("location_id", sa.Uuid, nullable=False),
    sa.Column("requested_price", sa.BigInteger, nullable=False),
    sa.Column("min_price", sa.BigInteger, nullable=False),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("requested_at", _TS, nullable=False),
    sa.Column("expires_at", _TS, nullable=False),
    sa.Column("decided_by", sa.Uuid, nullable=True),
    sa.Column("decided_at", _TS, nullable=True),
    sa.Column("sale_id", sa.Uuid, nullable=True),
    sa.Index("price_request_seller_idx", "shop_id", "seller_id", "requested_at"),
    sa.Index("price_request_status_idx", "shop_id", "status", "expires_at"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
    sa.CheckConstraint("requested_price >= 0", name="requested_price_non_negative"),
    sa.CheckConstraint("requested_price < min_price", name="requested_below_minimum"),
)

sale_return = sa.Table(
    "sale_return",
    metadata,
    *_identity(),
    sa.Column("sale_id", sa.Uuid, nullable=False),
    sa.Column("sale_number", sa.String(16), nullable=False),
    sa.Column("kind", sa.String(16), nullable=False),
    sa.Column("lines", sa.JSON, nullable=False),
    sa.Column("reason", sa.String(500), nullable=False),
    sa.Column("amount", sa.BigInteger, nullable=False),
    sa.Column("margin", sa.BigInteger, nullable=True),
    sa.Column("margin_wac", sa.BigInteger, nullable=True),
    sa.Column("refund_amount", sa.BigInteger, nullable=True),
    sa.Column("refund_mode_id", sa.Uuid, nullable=True),
    sa.Column("refunded_on", sa.Date, nullable=True),
    sa.Column("credit_reduction", sa.BigInteger, nullable=False),
    sa.Column("exchange_sale_id", sa.Uuid, nullable=True),
    sa.Column("returned_at", _TS, nullable=False),
    sa.Column("returned_on", sa.Date, nullable=False),
    sa.Column("created_by", sa.Uuid, nullable=False),
    sa.Index("sale_return_sale_idx", "shop_id", "sale_id"),
    sa.Index("sale_return_day_idx", "shop_id", "returned_on"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
    sa.CheckConstraint("amount >= 0", name="amount_non_negative"),
    sa.CheckConstraint("credit_reduction >= 0", name="credit_reduction_non_negative"),
    sa.CheckConstraint(
        "(refund_amount IS NULL) = (refund_mode_id IS NULL)", name="refund_complete"
    ),
)
