"""Costing (2/2) : rejeu du CMP et du dernier coût d'un article (RG-T11, RG-T12, UC-ACH-03/04).

**Décision client Q-02** : le CMP se rejoue sur le **stock réel** au moment de chaque entrée
coûtée. `replay_wac` reçoit **tous** les mouvements de l'article (tous lieux, tous états) et
les rejoue dans l'ordre chronologique `(date de l'opération, ordre d'enregistrement)` :

- une entrée coûtée (`sets_cost` : Entrée achat, Reprise de départ) recalcule le CMP par
  `next_wac` avec la quantité tenue **à cet instant**, puis s'y ajoute ;
- toute autre ligne (vente, retour, ajustement, déplacement…) ne change pas le CMP mais fait
  varier la quantité qui pondère les entrées suivantes (P1 10 x 500 000, vente de 5, P2
  5 x 530 000 → 515 000, recette SCN-04 v3).

Dernier coût (RG-T11) : coût de l'entrée coûtée la plus récente **par date d'opération** ;
égalité de date : la dernière enregistrée (ordre de création, décision Q-04).

Le tri et l'exclusion des mouvements annulés (une paire mouvement + « Annulation » disparaît,
« comme si saisi juste dès le départ ») sont faits par l'appelant qui connaît le grand livre ;
`replay_wac` retrie quand même par sécurité.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.domain.purchasing.costing import next_wac
from app.domain.shared.business_day import require_aware
from app.domain.shared.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class CostEvent:
    """Un mouvement vu par le Costing : quantité signée, coût, entrée coûtée ou non."""

    at: datetime
    order: UUID
    quantity: Decimal
    unit_cost: Money | None = None
    sets_cost: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "at", require_aware(self.at))
        if not isinstance(self.quantity, Decimal) or not self.quantity.is_finite():
            msg = "CostEvent.quantity doit être un Decimal fini"
            raise TypeError(msg)
        if self.sets_cost and (self.unit_cost is None or self.quantity <= 0):
            msg = "Une entrée coûtée exige un coût et une quantité > 0"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class CostState:
    """Résultat du rejeu : quantité tenue (tous lieux), CMP et dernier coût (`None` : inconnu)."""

    quantity: Decimal
    wac: Money | None
    last_cost: Money | None


def replay_wac(events: Iterable[CostEvent]) -> CostState:
    quantity, wac, last = Decimal(0), None, None
    for event in sorted(events, key=lambda e: (e.at, e.order)):
        if event.sets_cost and event.unit_cost is not None:
            wac = next_wac(quantity, wac, event.quantity, event.unit_cost)
            last = event.unit_cost
        quantity += event.quantity
    return CostState(quantity, wac, last)
