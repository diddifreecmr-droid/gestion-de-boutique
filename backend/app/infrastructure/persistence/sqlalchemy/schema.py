"""`metadata` partagée par tous les modules de tables (convention de nommage stable)."""

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
