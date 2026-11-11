"""Demandes adressées au grand livre (`StockLedger`) par les modules métier (T14, T15, T16, Lot 2).

`Posting` décrit un mouvement **sans signe** : `quantity` est la quantité déplacée (> 0) dans
l'unité de stock de l'article ; le type (`MovementType`) fixe le sens. Préconditions vérifiées
(erreur explicite sinon, rien n'est écrit) :

- l'article et le lieu existent dans la boutique de l'unité de travail (`NotFound`) ;
- le lieu est actif (`ValidationFailed`, champ `location_id`) ;
- `quantity.unit` est l'unité de stock de l'article (`ValueError` : erreur d'appelant) ;
- coût unitaire présent pour une Entrée achat / Reprise de départ, absent d'une sortie ;
- `occurred_at` : date de l'**opération** (aware) ; `author_id` : qui a saisi le document.
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.catalog.ids import ArticleId
from app.domain.shared.ids import UserId
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity
from app.domain.shops.ids import LocationId
from app.domain.stock.ids import StockMovementId
from app.domain.stock.values import MovementType, SourceRef, StockCondition


@dataclass(frozen=True, slots=True, kw_only=True)
class Posting:
    article_id: ArticleId
    location_id: LocationId
    type: MovementType
    quantity: Quantity
    source: SourceRef
    occurred_at: datetime
    author_id: UserId
    condition: StockCondition = StockCondition.SELLABLE
    unit_cost: Money | None = None

    def __post_init__(self) -> None:
        self.quantity.require_positive("quantity")


@dataclass(frozen=True, slots=True, kw_only=True)
class SignedPosting:
    """Forme interne : quantité signée, mode différé, mouvement inversé (`reverses`)."""

    posting: Posting
    signed: Quantity
    deferred: bool = False
    reverses: StockMovementId | None = None
