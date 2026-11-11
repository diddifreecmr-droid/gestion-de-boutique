"""Construction du moteur SQLAlchemy (pool de connexions) à partir d'une URL validée."""

from collections.abc import Mapping

import sqlalchemy as sa

READ_COMMITTED = "READ COMMITTED"
"""Isolation supposée par l'adaptateur (défaut de PostgreSQL), fixée explicitement."""


def create_sql_engine(
    url: str,
    *,
    isolation_level: str = READ_COMMITTED,
    pool_size: int = 5,
    connect_args: Mapping[str, object] | None = None,
) -> sa.Engine:
    """Moteur paresseux : aucune connexion n'est ouverte avant la première unité de travail.

    `pool_pre_ping` écarte les connexions coupées (redémarrage de la base) au lieu de faire
    échouer la requête suivante.
    """
    if not url.strip():
        msg = "URL de base de données vide"
        raise ValueError(msg)
    return sa.create_engine(
        url,
        isolation_level=isolation_level,
        pool_pre_ping=True,
        pool_size=pool_size,
        connect_args=dict(connect_args or {}),
    )
