"""Schéma SQL de production (cible des migrations Alembic, `alembic/env.py`).

Les tables métier rejoignent `metadata` avec leur module (T10+) ; chaque ajout s'accompagne
d'une migration. Conventions (specs § 5.1) : identifiants UUIDv7 fournis par l'application
(`sa.Uuid`, natif sur PostgreSQL, `CHAR(32)` ailleurs), `shop_id` en tête des index, `version`
pour le verrou optimiste, `BIGINT` pour les compteurs et montants. Aucun trigger ni procédure.
"""

import sqlalchemy as sa

NAMING_CONVENTION = {
    "pk": "%(table_name)s_pkey",
    "uq": "%(table_name)s_%(column_0_N_name)s_key",
    "ix": "%(table_name)s_%(column_0_N_name)s_idx",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
}
"""Noms explicites et stables (identiques sur toute base) : ils apparaissent dans les erreurs."""

metadata = sa.MetaData(naming_convention=NAMING_CONVENTION)

document_counter = sa.Table(
    "document_counter",
    metadata,
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("doc_type", sa.String(8), nullable=False),
    sa.Column("last_value", sa.BigInteger, nullable=False),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.PrimaryKeyConstraint("shop_id", "doc_type"),
    sa.CheckConstraint("last_value >= 1", name="last_value_positive"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
)
"""Dernier numéro définitif attribué, par boutique et par type (RG-T05, TR-10)."""

audit_entry = sa.Table(
    "audit_entry",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("actor_id", sa.Uuid, nullable=False),
    sa.Column("role", sa.String(64), nullable=False),
    sa.Column("device_id", sa.Uuid, nullable=True),
    sa.Column("action", sa.String(32), nullable=False),
    sa.Column("module", sa.String(64), nullable=False),
    sa.Column("entity_type", sa.String(64), nullable=False),
    sa.Column("entity_id", sa.Uuid, nullable=True),
    sa.Column("entity_number", sa.String(500), nullable=True),
    sa.Column("summary", sa.String(500), nullable=False),
    sa.Column("changes", sa.JSON, nullable=False),
    sa.Column("reason", sa.String(500), nullable=True),
    sa.Column("sensitive", sa.Boolean, nullable=False),
    sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    sa.Index("audit_entry_shop_received_idx", "shop_id", "received_at", "id"),
    sa.Index("audit_entry_shop_entity_idx", "shop_id", "entity_type", "entity_id"),
    sa.Index("audit_entry_shop_actor_idx", "shop_id", "actor_id", "received_at"),
)
"""Journal d'actions, en ajout seul (RG-J01) : aucune requête `UPDATE`/`DELETE` dans le code.

Index `(shop_id, received_at, id)` : sert le tri « plus récent d'abord » (`ORDER BY … DESC`)
par parcours inverse du B-tree, sans colonne `DESC` (expression d'index mal comparée par
`alembic check`)."""

alert = sa.Table(
    "alert",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.Column("recipient_id", sa.Uuid, nullable=False),
    sa.Column("type", sa.String(64), nullable=False),
    sa.Column("entity_type", sa.String(64), nullable=False),
    sa.Column("entity_id", sa.Uuid, nullable=False),
    sa.Column("entity_number", sa.String(500), nullable=True),
    sa.Column("message", sa.String(500), nullable=False),
    sa.Column("read", sa.Boolean, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("dedup_key", sa.String(200), nullable=True),
    sa.Column("dedup_active_key", sa.String(200), nullable=True),
    sa.UniqueConstraint("shop_id", "recipient_id", "dedup_active_key", name="alert_active_dedup"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
    sa.CheckConstraint(
        "dedup_active_key IS NULL OR dedup_active_key = dedup_key", name="dedup_active_matches"
    ),
    sa.Index("alert_shop_recipient_idx", "shop_id", "recipient_id", "created_at"),
)
"""Alertes (§ 20.1). Unicité « active + clé » portable : `dedup_active_key` = `dedup_key` tant
que l'alerte est active, `NULL` une fois résolue ; `UNIQUE` ignore les `NULL` (PostgreSQL,
SQLite, MySQL, Oracle), sans index partiel propre à un moteur."""

entitlement_override = sa.Table(
    "entitlement_override",
    metadata,
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("entitlement", sa.String(64), nullable=False),
    sa.Column("enabled", sa.Boolean, nullable=False),
    sa.Column("set_by", sa.Uuid, nullable=False),
    sa.Column("set_at", sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint("shop_id", "entitlement"),
)
"""Surcharges de droits d'offre posées par l'administrateur plateforme (TR-26, D17)."""
