"""Tables du stock (T14, specs § 5.3) : projection, grand livre, ajustements, inventaires.

- `stock_level` : une ligne par article x lieu (`stock_level_article_location`, nom de la
  `UniqueKey` du port), soldes `NUMERIC(12,1)`, `version` pour le verrou optimiste (D6).
- `stock_movement` : grand livre **en ajout seul** (aucun `UPDATE`/`DELETE` dans
  l'adaptateur) ; index `(shop_id, article_id, occurred_at, id)` pour l'historique,
  `(shop_id, location_id, type, recorded_at)` pour « ventes depuis le début du comptage » ;
  `stock_movement_reverses` : un mouvement ne s'annule qu'une fois (`NULL` non contraint).
- `inventory` : `inventory_open_location` = lieu tant que l'inventaire est en cours, `NULL`
  ensuite (unicité portable, comme `alert_active_dedup`) ; `inventory_line` : ses lignes.
- Aucune clé étrangère (intégrité garantie par l'application, comme pour le socle).
"""

import sqlalchemy as sa

from app.infrastructure.persistence.sqlalchemy.schema import metadata

_TS = sa.DateTime(timezone=True)
_QTY = sa.Numeric(12, 1)

stock_level = sa.Table(
    "stock_level",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.Column("article_id", sa.Uuid, nullable=False),
    sa.Column("location_id", sa.Uuid, nullable=False),
    sa.Column("unit", sa.String(8), nullable=False),
    sa.Column("sellable", _QTY, nullable=False),
    sa.Column("damaged", _QTY, nullable=False),
    sa.Column("incoming", _QTY, nullable=False),
    sa.UniqueConstraint(
        "shop_id", "article_id", "location_id", name="stock_level_article_location"
    ),
    sa.Index("stock_level_shop_location_idx", "shop_id", "location_id"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
)

stock_movement = sa.Table(
    "stock_movement",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("article_id", sa.Uuid, nullable=False),
    sa.Column("location_id", sa.Uuid, nullable=False),
    sa.Column("type", sa.String(24), nullable=False),
    sa.Column("condition", sa.String(16), nullable=False),
    sa.Column("unit", sa.String(8), nullable=False),
    sa.Column("quantity", _QTY, nullable=False),
    sa.Column("balance_after", _QTY, nullable=False),
    sa.Column("source_type", sa.String(16), nullable=False),
    sa.Column("source_id", sa.Uuid, nullable=False),
    sa.Column("source_number", sa.String(64), nullable=True),
    sa.Column("unit_cost", sa.BigInteger, nullable=True),
    sa.Column("occurred_at", _TS, nullable=False),
    sa.Column("recorded_at", _TS, nullable=False),
    sa.Column("author_id", sa.Uuid, nullable=False),
    sa.Column("stock_to_verify", sa.Boolean, nullable=False),
    sa.Column("reverses_id", sa.Uuid, nullable=True),
    sa.UniqueConstraint("shop_id", "reverses_id", name="stock_movement_reverses"),
    sa.Index("stock_movement_article_idx", "shop_id", "article_id", "occurred_at", "id"),
    sa.Index("stock_movement_location_idx", "shop_id", "location_id", "type", "recorded_at"),
    sa.Index("stock_movement_source_idx", "shop_id", "source_id"),
    sa.CheckConstraint("quantity <> 0", name="quantity_non_zero"),
    sa.CheckConstraint("unit_cost >= 0", name="unit_cost_non_negative"),
)

stock_adjustment = sa.Table(
    "stock_adjustment",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.Column("location_id", sa.Uuid, nullable=False),
    sa.Column("article_id", sa.Uuid, nullable=False),
    sa.Column("direction", sa.String(8), nullable=False),
    sa.Column("unit", sa.String(8), nullable=False),
    sa.Column("quantity", _QTY, nullable=False),
    sa.Column("condition", sa.String(16), nullable=False),
    sa.Column("reason", sa.String(24), nullable=False),
    sa.Column("note", sa.String(500), nullable=True),
    sa.Column("photo_id", sa.Uuid, nullable=True),
    sa.Column("inventory_id", sa.Uuid, nullable=True),
    sa.Column("created_at", _TS, nullable=False),
    sa.Column("author_id", sa.Uuid, nullable=False),
    sa.Index("stock_adjustment_article_idx", "shop_id", "article_id", "created_at"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
    sa.CheckConstraint("quantity > 0", name="quantity_positive"),
)

inventory = sa.Table(
    "inventory",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.Column("number", sa.String(32), nullable=False),
    sa.Column("location_id", sa.Uuid, nullable=False),
    sa.Column("open_location_id", sa.Uuid, nullable=True),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("started_at", _TS, nullable=False),
    sa.Column("closed_at", _TS, nullable=True),
    sa.Column("global_reason", sa.String(500), nullable=True),
    sa.UniqueConstraint("shop_id", "number", name="inventory_number"),
    sa.UniqueConstraint("shop_id", "open_location_id", name="inventory_open_location"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
)

inventory_line = sa.Table(
    "inventory_line",
    metadata,
    sa.Column("inventory_id", sa.Uuid, nullable=False),
    sa.Column("article_id", sa.Uuid, nullable=False),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("unit", sa.String(8), nullable=False),
    sa.Column("counted", _QTY, nullable=True),
    sa.Column("theoretical", _QTY, nullable=True),
    sa.Column("reason", sa.String(500), nullable=True),
    sa.Column("gap_value", sa.BigInteger, nullable=True),
    sa.PrimaryKeyConstraint("inventory_id", "article_id"),
)
"""Lignes d'un inventaire, réécrites avec lui (l'agrégat est enregistré d'un bloc)."""
