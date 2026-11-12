"""Variables du stockage des pièces jointes (D16, TR-17), lues avec les autres réglages.

`Settings` en hérite ; la règle croisée (`storage_problem`) est appelée par son validateur :

- `STORAGE_BACKEND` absent : `memory` si ENVIRONMENT=test, `s3` sinon ; `memory` interdit en prod ;
- `s3` exige `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` et `S3_BUCKET` (fail-fast) ;
- `ATTACHMENT_LINK_TTL_SECONDS` : durée des liens signés (60 s par défaut, specs § 8.2).
"""

from enum import StrEnum

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class StorageBackend(StrEnum):
    MEMORY = "memory"  # tests et démo : fichiers perdus à l'arrêt
    S3 = "s3"  # Silo (fork de MinIO) ou tout service compatible S3


class StorageVariables(BaseSettings):
    STORAGE_BACKEND: StorageBackend | None = None
    # http(s)://hôte[:port], sans chemin. En prod : http://silo:9000 (réseau interne).
    S3_ENDPOINT: str | None = Field(default=None, pattern=r"^https?://[^/\s]+/?$")
    S3_ACCESS_KEY: str | None = Field(default=None, min_length=3, max_length=128)
    S3_SECRET_KEY: SecretStr | None = None
    S3_BUCKET: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
    S3_REGION: str = Field(default="us-east-1", pattern=r"^[a-z0-9-]{2,32}$")
    ATTACHMENT_LINK_TTL_SECONDS: int = Field(default=60, ge=5, le=3600)

    def storage_backend_for(self, test_environment: bool) -> StorageBackend:
        if self.STORAGE_BACKEND is not None:
            return self.STORAGE_BACKEND
        return StorageBackend.MEMORY if test_environment else StorageBackend.S3

    def storage_problem(self, *, test_environment: bool, production: bool) -> str | None:
        """Message de l'incohérence de configuration, ou `None` si tout est fourni."""
        backend = self.storage_backend_for(test_environment)
        if backend is StorageBackend.MEMORY:
            if production:
                return "STORAGE_BACKEND=memory interdit en prod (fichiers perdus à l'arrêt)"
            return None
        required = {
            "S3_ENDPOINT": self.S3_ENDPOINT,
            "S3_ACCESS_KEY": self.S3_ACCESS_KEY,
            "S3_SECRET_KEY": self.S3_SECRET_KEY,
            "S3_BUCKET": self.S3_BUCKET,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            return f"{', '.join(missing)} obligatoire(s) avec STORAGE_BACKEND=s3"
        return None
