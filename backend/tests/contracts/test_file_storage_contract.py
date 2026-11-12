"""Contrat du port `FileStorage` (mémoire ; S3 avec `--storage=s3`, Silo de dev) : relecture
octet pour octet, réécriture, clé absente → `MissingFile`, service injoignable →
`StorageUnavailable` (jamais avalé, jamais bloquant)."""

import time

import pytest

from app.application.attachments.ports import FileStorage, MissingFile, StorageUnavailable
from app.domain.attachments.values import MAX_SIZE_BYTES, FileFormat
from app.infrastructure.storage.memory import MemoryFileStorage
from app.infrastructure.storage.s3 import S3FileStorage, S3Location
from tests.contracts.storage import file_storage, storage_prefix

__all__ = ["file_storage", "storage_prefix"]  # fixtures du banc

JPEG = b"\xff\xd8\xff\xe0" + bytes(range(256)) * 4


def test_written_bytes_are_read_back_identically(
    file_storage: FileStorage, storage_prefix: str
) -> None:
    key = f"{storage_prefix}a.jpg"
    file_storage.put(key, JPEG, FileFormat.JPEG)
    assert file_storage.get(key) == JPEG
    file_storage.put(key, b"%PDF-1.7 replaced", FileFormat.PDF)
    assert file_storage.get(key) == b"%PDF-1.7 replaced"


def test_a_five_megabyte_file_round_trips(file_storage: FileStorage, storage_prefix: str) -> None:
    content = b"\x89PNG\r\n\x1a\n" + b"\x07" * (MAX_SIZE_BYTES - 8)
    file_storage.put(f"{storage_prefix}big.png", content, FileFormat.PNG)
    assert file_storage.get(f"{storage_prefix}big.png") == content


def test_a_missing_key_is_an_integrity_error(
    file_storage: FileStorage, storage_prefix: str
) -> None:
    with pytest.raises(MissingFile):
        file_storage.get(f"{storage_prefix}absent.jpg")


def test_memory_storage_down_raises_storage_unavailable() -> None:
    storage = MemoryFileStorage()
    storage.available = False
    with pytest.raises(StorageUnavailable) as caught:
        storage.put("k.jpg", JPEG, FileFormat.JPEG)
    assert caught.value.code == "STORAGE_UNAVAILABLE"
    with pytest.raises(StorageUnavailable):
        storage.get("k.jpg")
    assert storage.keys() == []


def test_unreachable_s3_fails_fast_with_storage_unavailable() -> None:
    location = S3Location(
        endpoint="http://127.0.0.1:9",  # port « discard » : connexion refusée
        access_key="nobody",
        secret_key="nothing-0123456789",
        bucket="attachments",
        region="us-east-1",
    )
    storage = S3FileStorage(location)
    started = time.monotonic()
    with pytest.raises(StorageUnavailable):
        storage.put("k.jpg", JPEG, FileFormat.JPEG)
    with pytest.raises(StorageUnavailable):
        storage.get("k.jpg")
    with pytest.raises(StorageUnavailable):
        storage.bucket_exists()
    assert time.monotonic() - started < 30


@pytest.mark.parametrize("endpoint", ["ftp://silo:21", "http://silo:9000/chemin", "silo:9000"])
def test_invalid_endpoints_are_refused(endpoint: str) -> None:
    location = S3Location(
        endpoint=endpoint, access_key="a", secret_key="b", bucket="c", region="us-east-1"
    )
    with pytest.raises(ValueError, match="S3_ENDPOINT invalide"):
        S3FileStorage(location)
