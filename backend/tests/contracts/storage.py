"""Adaptateur `FileStorage` sous contrat (`--storage=memory|s3`).

    uv run pytest tests/contracts/test_file_storage_contract.py                  # mémoire
    uv run pytest tests/contracts/test_file_storage_contract.py --storage=s3     # Silo de dev

Avec `s3`, les variables `TEST_S3_ENDPOINT`, `TEST_S3_ACCESS_KEY`, `TEST_S3_SECRET_KEY` et
`TEST_S3_BUCKET` sont exigées ; absentes ou service injoignable, la session **échoue**
(`pytest.UsageError`), elle ne saute rien. Le bucket de test est créé s'il manque (banc de
tests seulement : en production, `silo-init` le crée privé) et chaque test écrit sous un
préfixe unique, effacé à la fin.
"""

import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
import urllib3

from app.application.attachments.ports import FileStorage
from app.infrastructure.storage.memory import MemoryFileStorage
from app.infrastructure.storage.s3 import S3FileStorage, S3Location

S3_VARIABLES = ("TEST_S3_ENDPOINT", "TEST_S3_ACCESS_KEY", "TEST_S3_SECRET_KEY", "TEST_S3_BUCKET")


def s3_location_from_env() -> S3Location:
    missing = [name for name in S3_VARIABLES if not os.environ.get(name, "").strip()]
    if missing:
        msg = f"--storage=s3 : variables absentes {missing} (voir infra/README.md)"
        raise pytest.UsageError(msg)
    return S3Location(
        endpoint=os.environ["TEST_S3_ENDPOINT"],
        access_key=os.environ["TEST_S3_ACCESS_KEY"],
        secret_key=os.environ["TEST_S3_SECRET_KEY"],
        bucket=os.environ["TEST_S3_BUCKET"],
        region=os.environ.get("TEST_S3_REGION", "us-east-1"),
    )


def _prepared(location: S3Location) -> S3Location:
    client = location.client()
    try:
        if not client.bucket_exists(location.bucket):
            client.make_bucket(location.bucket)
    except urllib3.exceptions.HTTPError as exc:
        msg = f"--storage=s3 : service S3 injoignable ({location.endpoint}) : {exc}"
        raise pytest.UsageError(msg) from exc
    return location


def _purge(location: S3Location, prefix: str) -> None:
    client = location.client()
    for item in client.list_objects(location.bucket, prefix=prefix, recursive=True):
        if item.object_name is not None:
            client.remove_object(location.bucket, item.object_name)


@pytest.fixture
def storage_prefix() -> str:
    return f"contract-tests/{uuid4()}/"


@pytest.fixture
def file_storage(request: pytest.FixtureRequest, storage_prefix: str) -> Iterator[FileStorage]:
    if request.config.getoption("--storage") == "memory":
        yield MemoryFileStorage()
        return
    location = _prepared(s3_location_from_env())
    yield S3FileStorage(location)
    _purge(location, storage_prefix)
