"""Banc de tests de contrat : la même suite sur chaque adaptateur (specs § 12.1, TR-02).

    uv run pytest tests/contracts --backend=memory     # défaut
    uv run pytest tests/contracts --backend=postgres   # TEST_DATABASE_URL requis

L'option `--backend` est déclarée dans `tests/conftest.py` (reconnue sur toute la suite).
"""

import pytest

from app.domain.shared.ids import ShopId
from tests.contracts.backends import ContractBackend, build_backend


@pytest.fixture
def backend(request: pytest.FixtureRequest) -> ContractBackend:
    return build_backend(str(request.config.getoption("--backend")))


@pytest.fixture
def shop_a() -> ShopId:
    return ShopId.new()


@pytest.fixture
def shop_b() -> ShopId:
    return ShopId.new()
