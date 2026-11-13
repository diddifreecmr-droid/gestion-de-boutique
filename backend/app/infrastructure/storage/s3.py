"""`FileStorage` sur un service compatible S3 : Silo (fork de MinIO, D16), MinIO, Garage, R2…

- Client `minio` (léger, signature SigV4), adressage par chemin (`http://hôte/bucket/clé`),
  région fixée par la configuration (aucun appel de découverte).
- Délais courts (connexion 3 s, lecture 15 s, 1 nouvelle tentative) : une panne remonte vite
  en `StorageUnavailable` (503) au lieu de bloquer un processus de l'API.
- Bucket **privé**, créé par `silo-init` (infra/) : l'adaptateur ne le crée ni ne change ses
  droits. Clé absente à la lecture → `MissingFile` (500, incohérence base ↔ stockage).
"""

import io
import logging
from dataclasses import dataclass
from urllib.parse import urlsplit

import urllib3
from minio import Minio
from minio.error import MinioException, S3Error

from app.application.attachments.ports import FileStorage, MissingFile, StorageUnavailable

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT_S = 3.0
READ_TIMEOUT_S = 15.0
RETRIES = 1
_MISSING_CODES = frozenset({"NoSuchKey", "NoSuchObject"})


@dataclass(frozen=True, slots=True, kw_only=True)
class S3Location:
    endpoint: str
    """URL du service, sans chemin : `http://silo:9000`, `https://s3.example.com`."""
    access_key: str
    secret_key: str
    bucket: str
    region: str

    def client(self) -> Minio:
        parts = urlsplit(self.endpoint)
        if parts.scheme not in ("http", "https") or not parts.netloc or parts.path not in ("", "/"):
            msg = f"S3_ENDPOINT invalide (attendu http(s)://hôte[:port]) : {self.endpoint!r}"
            raise ValueError(msg)
        http = urllib3.PoolManager(
            timeout=urllib3.Timeout(connect=CONNECT_TIMEOUT_S, read=READ_TIMEOUT_S),
            retries=urllib3.Retry(
                total=RETRIES, backoff_factor=0.2, status_forcelist=(502, 503, 504)
            ),
        )
        return Minio(
            parts.netloc,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=parts.scheme == "https",
            region=self.region,
            http_client=http,
        )


class S3FileStorage(FileStorage):
    def __init__(self, location: S3Location) -> None:
        self._bucket = location.bucket
        self._client = location.client()

    def put(self, key: str, content: bytes, media_type: str) -> None:
        try:
            self._client.put_object(
                self._bucket,
                key,
                io.BytesIO(content),
                len(content),
                content_type=str(media_type),
            )
        except (MinioException, urllib3.exceptions.HTTPError) as exc:
            raise _unavailable("écriture", key, exc) from exc

    def get(self, key: str) -> bytes:
        try:
            response = self._client.get_object(self._bucket, key)
        except S3Error as exc:
            if exc.code in _MISSING_CODES:
                msg = f"Objet absent du stockage : {key}"
                raise MissingFile(msg) from exc
            raise _unavailable("lecture", key, exc) from exc
        except (MinioException, urllib3.exceptions.HTTPError) as exc:
            raise _unavailable("lecture", key, exc) from exc
        try:
            return response.read()
        except urllib3.exceptions.HTTPError as exc:
            raise _unavailable("lecture", key, exc) from exc
        finally:
            response.close()
            response.release_conn()

    def bucket_exists(self) -> bool:
        """Bucket présent (tests d'intégration, diagnostic) ; panne → `StorageUnavailable`."""
        try:
            return bool(self._client.bucket_exists(self._bucket))
        except (MinioException, urllib3.exceptions.HTTPError) as exc:
            raise _unavailable("vérification", self._bucket, exc) from exc


def _unavailable(action: str, key: str, exc: Exception) -> StorageUnavailable:
    logger.error("Stockage S3 : %s impossible (%s) : %s", action, key, exc)
    msg = "Stockage des fichiers indisponible : réessayer"
    return StorageUnavailable(msg)
