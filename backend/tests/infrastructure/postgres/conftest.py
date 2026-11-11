"""Tests exigeant une vraie base : sautés **avec motif affiché** (`-ra`) sans `--backend=postgres`.

Ils ne sont pas dans le contrat commun : sur PostgreSQL, une écriture concurrente **attend** le
verrou de ligne de l'autre transaction, ce qu'un test monothread ne peut pas exprimer.
"""

import pytest

from app.domain.shared.ids import ShopId
from tests.contracts.backends.postgres import PostgresContractBackend

REASON = "PostgreSQL requis : uv run pytest tests/infrastructure/postgres --backend=postgres"


@pytest.fixture
def pg(request: pytest.FixtureRequest) -> PostgresContractBackend:
    if request.config.getoption("--backend") != "postgres":
        pytest.skip(REASON)
    return PostgresContractBackend()


@pytest.fixture
def shop() -> ShopId:
    return ShopId.new()
