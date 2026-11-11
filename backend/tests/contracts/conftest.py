"""Banc de tests de contrat : la même suite sur chaque adaptateur (specs § 12.1, TR-02).

    uv run pytest tests/contracts --backend=memory     # défaut
    uv run pytest tests/contracts --backend=postgres   # T06 : échoue explicitement en T05

L'option est déclarée ici (et non dans `tests/conftest.py`) : elle n'est donc reconnue sur la
ligne de commande que si `tests/contracts` (ou un de ses fichiers) est passé à pytest. Lancée
sans chemin, la suite complète exécute les contrats sur l'adaptateur par défaut.
"""

import pytest

from app.domain.shared.ids import ShopId
from tests.contracts.backends import (
    BACKENDS,
    DEFAULT_BACKEND,
    ContractBackend,
    build_backend,
    require_available,
)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--backend",
        choices=BACKENDS,
        default=DEFAULT_BACKEND,
        help="Adaptateur de persistance sous contrat (tests/contracts).",
    )


def pytest_configure(config: pytest.Config) -> None:
    require_available(str(config.getoption("--backend")))


@pytest.fixture
def backend(request: pytest.FixtureRequest) -> ContractBackend:
    return build_backend(str(request.config.getoption("--backend")))


@pytest.fixture
def shop_a() -> ShopId:
    return ShopId.new()


@pytest.fixture
def shop_b() -> ShopId:
    return ShopId.new()
