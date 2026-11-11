"""Statut HTTP du catalogue fin d'erreurs (§ 6.2) : hérité du type générique le plus proche."""

import pytest

from app.domain.shared.errors import (
    DateOutOfRange,
    DomainError,
    Duplicate,
    InvalidAmount,
    InvalidIdentifier,
    InvalidQuantity,
    InvalidStateTransition,
    VersionConflict,
)
from app.interface.http.errors import status_for


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (VersionConflict("Objet modifié entre-temps"), 409),
        (Duplicate("Téléphone déjà utilisé"), 409),
        (InvalidAmount("Montant négatif"), 400),
        (InvalidQuantity("Trop de décimales"), 400),
        (InvalidIdentifier("Identifiant illisible"), 400),
        (DateOutOfRange("Date future"), 422),
        (InvalidStateTransition("Vente déjà annulée"), 422),
    ],
)
def test_fine_errors_map_to_expected_status(error: DomainError, status: int) -> None:
    assert status_for(error) == status
