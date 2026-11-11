"""`StockMovement` : une ligne **immuable** du grand livre de stock (RG-T16, H21, CDC § 20.2).

- Quantité **signée** dans l'unité de stock de l'article (Decimal, RG-T08), jamais nulle ; son
  signe est imposé par le type (`MovementType.direction`).
- État : Vendable ou Abîmé — le mouvement ne touche que le solde de cet état.
- Coût unitaire : obligatoire pour une Entrée achat ou une Reprise de départ (`COSTED_ENTRIES`),
  interdit sur une sortie (le coût d'une vente est figé par la vente elle-même, T16).
- `balance_after` : solde du lieu **dans cet état** après le mouvement (« Stock après »).
- `occurred_at` : date de l'opération (pas de la saisie) ; `recorded_at` : enregistrement.
- `stock_to_verify` : sortie différée acceptée qui a rendu le solde négatif (RG-T18).
- `reverses` : mouvement annulé par ce mouvement « Annulation » (quantité opposée).

Le stock n'est jamais tapé : seul `StockLedger` (application) crée un mouvement et met à jour
la projection `StockLevel` dans la même transaction (TR-13).
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.catalog.ids import ArticleId
from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import InvalidQuantity, ValidationFailed
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity
from app.domain.shops.ids import LocationId
from app.domain.stock.ids import StockMovementId
from app.domain.stock.values import (
    COSTED_ENTRIES,
    Direction,
    MovementType,
    SourceRef,
    StockCondition,
)


def check_sign(movement_type: MovementType, quantity: Quantity) -> None:
    """Quantité non nulle, du signe imposé par le type (`InvalidQuantity` sinon)."""
    direction = MovementType(movement_type).direction
    value = quantity.value
    wrong = (
        value == 0
        or (direction is Direction.IN and value < 0)
        or (direction is Direction.OUT and value > 0)
    )
    if wrong:
        msg = "Quantité de mouvement incompatible avec son type"
        raise InvalidQuantity(
            msg, details={"field": "quantity", "type": movement_type.value, "value": str(value)}
        )


def check_cost(movement_type: MovementType, unit_cost: Money | None) -> None:
    """Coût exigé sur une entrée coûtée, refusé sur une sortie ; jamais négatif (RG-T07)."""
    if unit_cost is not None:
        unit_cost.require_non_negative("unit_cost")
    if movement_type in COSTED_ENTRIES and unit_cost is None:
        msg = "Coût unitaire obligatoire pour une entrée"
        raise ValidationFailed(msg, details={"field": "unit_cost", "type": movement_type.value})
    if movement_type.direction is Direction.OUT and unit_cost is not None:
        msg = "Une sortie ne porte pas de coût unitaire"
        raise ValidationFailed(msg, details={"field": "unit_cost", "type": movement_type.value})


@dataclass(frozen=True, slots=True, kw_only=True)
class StockMovement:
    id: StockMovementId
    shop_id: ShopId
    article_id: ArticleId
    location_id: LocationId
    type: MovementType
    condition: StockCondition
    quantity: Quantity
    balance_after: Quantity
    source: SourceRef
    occurred_at: datetime
    recorded_at: datetime
    author_id: UserId
    unit_cost: Money | None = None
    stock_to_verify: bool = False
    reverses: StockMovementId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "type", MovementType(self.type))
        object.__setattr__(self, "condition", StockCondition(self.condition))
        for name, kind in (("article_id", ArticleId), ("location_id", LocationId)):
            if not isinstance(getattr(self, name), kind):
                msg = f"StockMovement.{name} doit être un {kind.__name__}"
                raise TypeError(msg)
        if self.balance_after.unit is not self.quantity.unit:
            msg = "StockMovement : quantité et solde dans des unités différentes"
            raise ValueError(msg)
        check_sign(self.type, self.quantity)
        if self.type is not MovementType.REVERSAL:
            check_cost(self.type, self.unit_cost)
        if (self.type is MovementType.REVERSAL) != (self.reverses is not None):
            msg = "Seule une Annulation désigne le mouvement qu'elle inverse"
            raise ValueError(msg)
        object.__setattr__(self, "occurred_at", require_aware(self.occurred_at))
        object.__setattr__(self, "recorded_at", require_aware(self.recorded_at))
