"""Environnement Alembic : applique les migrations sur la base de l'adaptateur SQL.

Connexion, par ordre de priorité :

1. `config.attributes["connection"]` : connexion fournie par l'appelant (tests) ;
2. `DATABASE_URL` validée par `app.bootstrap.config.load_database_url` (environnement ou
   `.env`) : migrer n'exige aucune autre variable.

Sans URL, la commande échoue explicitement (jamais de base implicite).
"""

from logging.config import fileConfig

import sqlalchemy as sa

from alembic import context
from app.bootstrap.config import load_database_url
from app.infrastructure.persistence.sqlalchemy.tables import metadata

config = context.config
if config.config_file_name is not None and "connection" not in config.attributes:
    # Ligne de commande : journal `alembic.ini`. Appel programmatique (tests) : rien n'est touché.
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def declared_only(name: str | None, type_: str, parent_names: object) -> bool:
    """Autogénération : ignore les tables inconnues du schéma (ex. `widget` du banc de tests)."""
    return type_ != "table" or name in metadata.tables


def run_on(connection: sa.Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=metadata,
        compare_type=True,
        include_name=declared_only,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    provided = config.attributes.get("connection")
    if isinstance(provided, sa.Connection):
        run_on(provided)
        return
    engine = sa.create_engine(load_database_url(), poolclass=sa.pool.NullPool)
    try:
        with engine.connect() as connection:
            run_on(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    context.configure(url=load_database_url(), target_metadata=metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    run_migrations_online()
