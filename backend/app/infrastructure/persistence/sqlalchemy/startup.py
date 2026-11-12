"""Vérification de la base **au démarrage** de l'API (fail-fast, T25).

Le moteur SQLAlchemy est paresseux : sans cette vérification, une base injoignable ou non
migrée ne se verrait qu'à la première requête d'un utilisateur. Ici, l'API refuse de démarrer
avec un message explicite (sans le mot de passe), et le conteneur redémarre jusqu'à ce que la
base réponde (politique `restart` du compose de production).

Deux contrôles :

1. connexion + `SELECT 1` ;
2. présence de la table `alembic_version` avec une révision : une base vide (migrations non
   appliquées) est refusée au lieu de produire des erreurs SQL plus tard.
"""

import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError

MIGRATIONS_TABLE = "alembic_version"


class DatabaseUnavailable(RuntimeError):
    """Base injoignable ou non migrée au démarrage : l'API ne démarre pas."""


def _where(engine: sa.Engine) -> str:
    return engine.url.render_as_string(hide_password=True)


def verify_database(engine: sa.Engine) -> str:
    """Retourne la révision Alembic courante ; lève `DatabaseUnavailable` sinon."""
    try:
        with engine.connect() as connection:
            connection.execute(sa.text("SELECT 1"))
            if not sa.inspect(connection).has_table(MIGRATIONS_TABLE):
                msg = (
                    f"Base {_where(engine)} non migrée (table {MIGRATIONS_TABLE} absente) : "
                    "lancer `alembic upgrade head` avant l'API"
                )
                raise DatabaseUnavailable(msg)
            revision = connection.execute(
                sa.text(f"SELECT version_num FROM {MIGRATIONS_TABLE}")
            ).scalar()
    except SQLAlchemyError as exc:
        reason = exc.__class__.__name__
        msg = f"Base de données injoignable au démarrage ({_where(engine)}) : {reason}"
        raise DatabaseUnavailable(msg) from exc
    if not revision:
        msg = f"Base {_where(engine)} sans révision Alembic : lancer `alembic upgrade head`"
        raise DatabaseUnavailable(msg)
    return str(revision)
