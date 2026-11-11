"""Contrat applicatif de `POST /sync` (specs § 6.5) : lot reçu, décodage, résultat par opération.

- `SyncBatch` : `{device_id, operations: [{op_id, type, provisional_number, captured_at,
  payload}]}`, traité **dans l'ordre** de la liste (ordre de saisie, RG-T23) ;
- `OperationDecoder` : traduit le `payload` brut en saisie du cas d'utilisation (fourni par
  l'interface, qui valide le JSON comme `POST /sales` ou `POST /expenses`) ; un payload
  invalide lève `ValidationFailed` → opération `rejected`, les suivantes continuent ;
- `OperationResult` : `accepted | duplicate | rejected`, numéro définitif et provisoire,
  avertissements (`STOCK_TO_VERIFY`, RG-T18) et erreur.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.application.expenses.references import ExpenseInput
from app.application.sales.inputs import SaleInput
from app.domain.shared.ids import DeviceId
from app.domain.sync.operation import SyncOperationId

MAX_OPERATIONS = 50
"""Taille maximale d'un lot (le client envoie par lots de 20, specs § 6.5)."""


class OperationType(StrEnum):
    """Saisies possibles hors connexion (RG-T22)."""

    SALE_CREATE = "sale.create"
    EXPENSE_CREATE = "expense.create"
    TRIP_STEP_CREATE = "trip_step.create"
    TRIP_EXPENSE_CREATE = "trip_expense.create"


LOT_2_TYPES = frozenset({OperationType.TRIP_STEP_CREATE, OperationType.TRIP_EXPENSE_CREATE})


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationInput:
    op_id: SyncOperationId
    type: str
    """Texte brut : un type inconnu est **refusé** (opération `rejected`), pas la requête."""
    captured_at: datetime
    provisional_number: str | None = None
    payload: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True, kw_only=True)
class SyncBatch:
    device_id: DeviceId
    operations: tuple[OperationInput, ...]


class OperationDecoder(Protocol):
    """Lecture du `payload` (interface HTTP) ; lève `ValidationFailed` s'il est invalide."""

    def sale(self, op_id: SyncOperationId, payload: Mapping[str, object]) -> SaleInput: ...

    def expense(self, op_id: SyncOperationId, payload: Mapping[str, object]) -> ExpenseInput: ...


class ResultStatus(StrEnum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class OperationNotice:
    """Avertissement ou erreur d'une opération : code stable, message, détails."""

    code: str
    message: str
    details: Mapping[str, object] = field(default_factory=dict)


STOCK_TO_VERIFY = OperationNotice(
    "STOCK_TO_VERIFY",
    "Stock devenu négatif après cette vente différée : à vérifier (alerte envoyée)",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationResult:
    op_id: SyncOperationId
    status: ResultStatus
    provisional_number: str | None
    number: str | None = None
    entity_id: UUID | None = None
    warnings: tuple[OperationNotice, ...] = ()
    error: OperationNotice | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Outcome:
    """Ce que renvoie l'exécution d'une opération acceptée (document créé ou déjà connu)."""

    entity_id: UUID
    number: str
    created: bool
    warnings: tuple[OperationNotice, ...] = ()
