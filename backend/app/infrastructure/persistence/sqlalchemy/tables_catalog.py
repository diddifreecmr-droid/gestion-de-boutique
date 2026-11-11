"""Tables du catalogue (T13) : `article` et `price_history` (specs § 5.3, § 4.5).

- Champs propres au profil (cylindrée, catégorie, type…) dans `attributes` (JSON), validés par
  le **domaine** (`domain/catalog/schema.py`), jamais par la base.
- Champs à unicité promus en colonnes : `brand_model_key` et `reference_key` (clés pliées,
  `NULL` = non contraint) portent les contraintes `article_brand_model` / `article_reference`,
  noms des `UniqueKey` du port (`application/catalog/ports.py`).
- `search_key` (recherche en sous-chaîne) et `sort_key` (ordre et curseur) sont calculés par
  le domaine : index `(shop_id, sort_key, id)` pour la liste paginée.
- Montants `BIGINT` ≥ 0 (`CHECK`) ; quantités `NUMERIC(12,1)` ; aucune clé étrangère
  (intégrité garantie par l'application, comme pour le socle).
"""

import sqlalchemy as sa

from app.infrastructure.persistence.sqlalchemy.schema import metadata

_TS = sa.DateTime(timezone=True)
_PRICES = ("base_price", "base_price_piece", "min_price", "min_price_piece", "last_cost", "wac")

article = sa.Table(
    "article",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.Column("display_name", sa.String(250), nullable=False),
    sa.Column("brand", sa.String(120), nullable=True),
    sa.Column("model", sa.String(120), nullable=True),
    sa.Column("reference", sa.String(120), nullable=True),
    sa.Column("brand_model_key", sa.String(250), nullable=True),
    sa.Column("reference_key", sa.String(250), nullable=True),
    sa.Column("search_key", sa.String(250), nullable=False),
    sa.Column("sort_key", sa.String(250), nullable=False),
    sa.Column("stock_unit", sa.String(8), nullable=False),
    sa.Column("sold_by_piece", sa.Boolean, nullable=False),
    sa.Column("piece_length_m", sa.Numeric(8, 2), nullable=True),
    sa.Column("alert_threshold", sa.Numeric(12, 1), nullable=True),
    sa.Column("photo_id", sa.Uuid, nullable=True),
    sa.Column("notes", sa.String(500), nullable=True),
    sa.Column("attributes", sa.JSON, nullable=False),
    *(sa.Column(name, sa.BigInteger, nullable=True) for name in _PRICES),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("created_at", _TS, nullable=False),
    sa.UniqueConstraint("shop_id", "brand_model_key", name="article_brand_model"),
    sa.UniqueConstraint("shop_id", "reference_key", name="article_reference"),
    sa.Index("article_shop_sort_idx", "shop_id", "sort_key", "id"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
    *(sa.CheckConstraint(f"{name} >= 0", name=f"{name}_non_negative") for name in _PRICES),
)

price_history = sa.Table(
    "price_history",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("article_id", sa.Uuid, nullable=False),
    sa.Column("price_kind", sa.String(24), nullable=False),
    sa.Column("old_price", sa.BigInteger, nullable=True),
    sa.Column("new_price", sa.BigInteger, nullable=True),
    sa.Column("effective_at", _TS, nullable=False),
    sa.Column("author_id", sa.Uuid, nullable=False),
    sa.Index("price_history_article_idx", "shop_id", "article_id", "effective_at"),
)
"""Historique des prix, en ajout seul (aucun `UPDATE` ni `DELETE` dans l'adaptateur)."""
