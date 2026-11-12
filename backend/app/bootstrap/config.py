"""Configuration lue dans l'environnement (et `.env` local), validée au démarrage.

Fail-fast (TR-25) : une variable manquante ou invalide lève `ConfigurationError` avec la liste
explicite des variables fautives ; l'application ne démarre pas.
"""

from enum import StrEnum
from ipaddress import IPv4Network, IPv6Network
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_core import ErrorDetails
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from app.bootstrap.storage_config import StorageBackend, StorageVariables

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

DEFAULT_ENV_FILE = Path(".env")
JWT_SECRET_MIN_BYTES = 32


class Environment(StrEnum):
    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class PersistenceBackend(StrEnum):
    MEMORY = "memory"  # tests et démo : tout est perdu à l'arrêt
    POSTGRES = "postgres"


class ConfigurationError(RuntimeError):
    """Configuration absente ou invalide : arrêt immédiat du démarrage."""


_SETTINGS_CONFIG = SettingsConfigDict(
    case_sensitive=True,
    extra="ignore",  # l'environnement du système contient d'autres variables
    frozen=True,
    env_file_encoding="utf-8",
)


def check_database_url(value: SecretStr) -> SecretStr:
    """URL SQLAlchemy lisible et qui nomme sa base ; `ValueError` sinon."""
    try:
        url = make_url(value.get_secret_value())
    except ArgumentError as exc:
        msg = "URL SQLAlchemy illisible (attendu : postgresql+psycopg://…)"
        raise ValueError(msg) from exc
    if not url.database:
        msg = "l'URL doit nommer la base (…/nom_de_base)"
        raise ValueError(msg)
    return value


class Settings(StorageVariables):
    """Variables reconnues (stockage : `StorageVariables`). Voir `backend/.env.example`."""

    model_config = _SETTINGS_CONFIG

    ENVIRONMENT: Environment
    API_PREFIX: str = Field(default="/api/v1", pattern=r"^(/[a-z0-9][a-z0-9_-]*)+$")
    LOG_LEVEL: LogLevel = "INFO"
    # Absent : `memory` si ENVIRONMENT=test, `postgres` sinon (voir `persistence_backend`).
    PERSISTENCE_BACKEND: PersistenceBackend | None = None
    # Secret : l'URL porte le mot de passe, jamais affiché (repr, journaux).
    DATABASE_URL: SecretStr | None = None

    @field_validator("DATABASE_URL")
    @classmethod
    def _parse_database_url(cls, value: SecretStr | None) -> SecretStr | None:
        return None if value is None else check_database_url(value)

    # Identité et sessions (T08, specs § 7.2, § 15.1)
    JWT_SECRET: SecretStr
    ACCESS_TOKEN_TTL_MINUTES: int = Field(default=15, ge=1, le=60)
    REFRESH_TOKEN_TTL_DAYS: int = Field(default=30, ge=1, le=365)
    ADMIN_SESSION_TTL_HOURS: int = Field(default=8, ge=1, le=24)

    # Limitation de débit de /auth/* (T10, T10b, specs § 8.1). Absent : active sauf
    # ENVIRONMENT=test. Seuils par minute et par IP, sauf le numéro (par fenêtre ci-dessous).
    AUTH_RATE_LIMIT_ENABLED: bool | None = None
    AUTH_RATE_LIMIT_LOGIN_PER_IP: int = Field(default=10, ge=1, le=10_000)
    AUTH_RATE_LIMIT_LOGIN_PER_PHONE: int = Field(default=5, ge=1, le=1_000)
    AUTH_RATE_LIMIT_PHONE_WINDOW_MINUTES: int = Field(default=15, ge=1, le=1_440)
    AUTH_RATE_LIMIT_REFRESH_PER_IP: int = Field(default=30, ge=1, le=10_000)
    AUTH_RATE_LIMIT_CHANGE_PIN_PER_IP: int = Field(default=10, ge=1, le=10_000)
    # IP/CIDR séparés par des virgules ; seuls eux peuvent fournir X-Forwarded-For (Caddy, T25).
    AUTH_TRUSTED_PROXIES: Annotated[tuple[IPv4Network | IPv6Network, ...], NoDecode] = ()

    @field_validator("AUTH_TRUSTED_PROXIES", mode="before")
    @classmethod
    def _split_proxies(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(part.strip() for part in value.split(",") if part.strip())
        return value

    @field_validator("JWT_SECRET")
    @classmethod
    def _strong_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode("utf-8")) < JWT_SECRET_MIN_BYTES:
            msg = f"au moins {JWT_SECRET_MIN_BYTES} octets exigés"
            raise ValueError(msg)
        return value

    @property
    def persistence_backend(self) -> PersistenceBackend:
        if self.PERSISTENCE_BACKEND is not None:
            return self.PERSISTENCE_BACKEND
        if self.ENVIRONMENT is Environment.TEST:
            return PersistenceBackend.MEMORY
        return PersistenceBackend.POSTGRES

    @property
    def storage_backend(self) -> StorageBackend:
        return self.storage_backend_for(self.ENVIRONMENT is Environment.TEST)

    @model_validator(mode="after")
    def _require_database(self) -> Self:
        backend = self.persistence_backend
        if backend is PersistenceBackend.POSTGRES and self.DATABASE_URL is None:
            msg = "DATABASE_URL est obligatoire avec PERSISTENCE_BACKEND=postgres"
            raise ValueError(msg)
        if backend is PersistenceBackend.MEMORY and self.ENVIRONMENT is Environment.PROD:
            msg = "PERSISTENCE_BACKEND=memory interdit en prod (données perdues à l'arrêt)"
            raise ValueError(msg)
        problem = self.storage_problem(
            test_environment=self.ENVIRONMENT is Environment.TEST,
            production=self.ENVIRONMENT is Environment.PROD,
        )
        if problem is not None:
            raise ValueError(problem)
        return self


def _describe(error: ErrorDetails) -> str:
    location = ".".join(str(part) for part in error["loc"])
    return f"{location} : {error['msg']}" if location else error["msg"]  # règle croisée : sans loc


class MigrationSettings(BaseSettings):
    """Sous-ensemble lu par Alembic : migrer n'exige que la base (ni secret JWT ni réglage HTTP)."""

    model_config = _SETTINGS_CONFIG

    DATABASE_URL: SecretStr

    @field_validator("DATABASE_URL")
    @classmethod
    def _parse_database_url(cls, value: SecretStr) -> SecretStr:
        return check_database_url(value)


def _invalid(exc: ValidationError) -> ConfigurationError:
    problems = "; ".join(_describe(error) for error in exc.errors(include_url=False))
    return ConfigurationError(f"Configuration invalide — {problems}")


def load_settings(env_file: Path | None = DEFAULT_ENV_FILE) -> Settings:
    """Construit les réglages ou lève `ConfigurationError` avec un message explicite."""
    try:
        return Settings(_env_file=env_file)
    except ValidationError as exc:
        raise _invalid(exc) from exc


def load_database_url(env_file: Path | None = DEFAULT_ENV_FILE) -> str:
    """`DATABASE_URL` validée (migrations) ; `ConfigurationError` si absente ou invalide."""
    try:
        settings = MigrationSettings(_env_file=env_file)
    except ValidationError as exc:
        raise _invalid(exc) from exc
    return settings.DATABASE_URL.get_secret_value()
