"""Configuration lue dans l'environnement (et `.env` local), validée au démarrage.

Fail-fast (TR-25) : une variable manquante ou invalide lève `ConfigurationError` avec la liste
explicite des variables fautives ; l'application ne démarre pas.
"""

from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

DEFAULT_ENV_FILE = Path(".env")


class Environment(StrEnum):
    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class ConfigurationError(RuntimeError):
    """Configuration absente ou invalide : arrêt immédiat du démarrage."""


class Settings(BaseSettings):
    """Variables reconnues. Voir `backend/.env.example`."""

    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore",  # l'environnement du système contient d'autres variables
        frozen=True,
        env_file_encoding="utf-8",
    )

    ENVIRONMENT: Environment
    API_PREFIX: str = Field(default="/api/v1", pattern=r"^(/[a-z0-9][a-z0-9_-]*)+$")
    LOG_LEVEL: LogLevel = "INFO"


def load_settings(env_file: Path | None = DEFAULT_ENV_FILE) -> Settings:
    """Construit les réglages ou lève `ConfigurationError` avec un message explicite."""
    try:
        return Settings(_env_file=env_file)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])} : {error['msg']}"
            for error in exc.errors(include_url=False)
        )
        msg = f"Configuration invalide — {problems}"
        raise ConfigurationError(msg) from exc
