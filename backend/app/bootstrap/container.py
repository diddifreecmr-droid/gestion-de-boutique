"""Composition root (specs § 4.1, règle 5) : seul module qui assemble les adaptateurs concrets.

Point d'entrée ASGI : `uvicorn app.bootstrap.container:build_app --factory`.
"""

import logging
from pathlib import Path

from fastapi import FastAPI

from app.bootstrap.config import DEFAULT_ENV_FILE, Environment, Settings, load_settings
from app.bootstrap.identity import build_identity
from app.bootstrap.persistence import build_unit_of_work_factory
from app.interface.http.app import create_app
from app.interface.http.config import HttpConfig

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(format=_LOG_FORMAT)
    logging.getLogger("app").setLevel(settings.LOG_LEVEL)


def http_config_from(settings: Settings) -> HttpConfig:
    """Traduit la configuration globale en configuration de l'adaptateur HTTP."""
    return HttpConfig(
        api_prefix=settings.API_PREFIX,
        expose_docs=settings.ENVIRONMENT is not Environment.PROD,
    )


def build_app(env_file: Path | None = DEFAULT_ENV_FILE) -> FastAPI:
    """Lit la configuration (fail-fast), configure la journalisation, assemble l'application."""
    settings = load_settings(env_file)
    configure_logging(settings)
    app = create_app(http_config_from(settings), build_identity(settings).auth)
    # Consommée par les routes à venir (T08+) ; adaptateur choisi par PERSISTENCE_BACKEND.
    app.state.uow_factory = build_unit_of_work_factory(settings)
    return app
