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
