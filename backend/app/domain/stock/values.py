"""Vocabulaire du grand livre de stock (CDC § 20.2 « Mouvement de stock », UC-STK-06).

- `MovementType` : les douze types du CDC, chacun avec son **sens** imposé (`Direction`) :
  une entrée a une quantité > 0, une sortie < 0 ; « Annulation » et « Remise en vente » sont
  libres (elles inversent ou déplacent un état) mais jamais nulles.
- `COSTED_ENTRIES` : entrées dont le coût unitaire est **obligatoire** (« Oui pour une
  entrée », il alimente le CMP, RG-T12) : Entrée achat et Reprise de départ. Les autres entrées
  (Retour client, Ajustement +, Arrivée de déplacement) le portent si l'appelant le connaît
  (décision Q-16 : l'ajustement + porte le CMP courant de l'article, ou rien).
- `StockCondition` : Vendable ou Abîmé (deux soldes distincts de la projection).
- `SourceRef` : document lié (achat, vente, retour, déplacement, ajustement, inventaire, lot
  d'import), avec son numéro lisible quand il en a un (`A-000001`, `INV-000001`).
"""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.domain.audit.values import require_text


class Direction(StrEnum):
    IN = "in"
    OUT = "out"
    EITHER = "either"


class MovementType(StrEnum):
    PURCHASE_IN = "purchase_in"  # Entrée achat
    SALE_OUT = "sale_out"  # Sortie vente
    CUSTOMER_RETURN = "customer_return"  # Retour client
    TRANSFER_OUT = "transfer_out"  # Départ déplacement
    TRANSFER_IN = "transfer_in"  # Arrivée déplacement
    TRANSFER_MISSING = "transfer_missing"  # Manquant au déplacement
    ADJUSTMENT_IN = "adjustment_in"  # Ajustement +
    ADJUSTMENT_OUT = "adjustment_out"  # Ajustement -
    OFFCUT = "offcut"  # Chute (RG-X06)
    OPENING = "opening"  # Reprise de départ (import)
    RESTORE = "restore"  # Remise en vente (UC-TRF-05)
    REVERSAL = "reversal"  # Annulation (inverse un mouvement)

    @property
    def direction(self) -> Direction:
        return _DIRECTIONS[self]

    @property
    def label(self) -> str:
        return _LABELS[self]


_DIRECTIONS = {
    MovementType.PURCHASE_IN: Direction.IN,
    MovementType.SALE_OUT: Direction.OUT,
    MovementType.CUSTOMER_RETURN: Direction.IN,
    MovementType.TRANSFER_OUT: Direction.OUT,
    MovementType.TRANSFER_IN: Direction.IN,
    MovementType.TRANSFER_MISSING: Direction.OUT,
    MovementType.ADJUSTMENT_IN: Direction.IN,
    MovementType.ADJUSTMENT_OUT: Direction.OUT,
    MovementType.OFFCUT: Direction.OUT,
    MovementType.OPENING: Direction.IN,
    MovementType.RESTORE: Direction.EITHER,
    MovementType.REVERSAL: Direction.EITHER,
}
_LABELS = {
    MovementType.PURCHASE_IN: "Entrée achat",
    MovementType.SALE_OUT: "Sortie vente",
    MovementType.CUSTOMER_RETURN: "Retour client",
    MovementType.TRANSFER_OUT: "Départ déplacement",
    MovementType.TRANSFER_IN: "Arrivée déplacement",
    MovementType.TRANSFER_MISSING: "Manquant au déplacement",
    MovementType.ADJUSTMENT_IN: "Ajustement +",
    MovementType.ADJUSTMENT_OUT: "Ajustement -",
    MovementType.OFFCUT: "Chute",
    MovementType.OPENING: "Reprise de départ",
    MovementType.RESTORE: "Remise en vente",
    MovementType.REVERSAL: "Annulation",
}

ENTRY_TYPES = frozenset(t for t in MovementType if t.direction is Direction.IN)
EXIT_TYPES = frozenset(t for t in MovementType if t.direction is Direction.OUT)
COSTED_ENTRIES = frozenset({MovementType.PURCHASE_IN, MovementType.OPENING})


class StockCondition(StrEnum):
    SELLABLE = "sellable"  # Vendable
    DAMAGED = "damaged"  # Abîmé


class SourceType(StrEnum):
    """Nature du document lié (CDC § 20.2 « Document lié »)."""

    PURCHASE = "purchase"
    SALE = "sale"
    RETURN = "return"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    INVENTORY = "inventory"
    IMPORT = "import"


@dataclass(frozen=True, slots=True)
class SourceRef:
    """Document à l'origine d'un mouvement (type, identifiant, numéro lisible facultatif)."""

    type: SourceType
    id: UUID
    number: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "type", SourceType(self.type))
        if not isinstance(self.id, UUID):
            msg = "SourceRef.id doit être un UUID"
            raise TypeError(msg)
        require_text(self.number, "SourceRef.number", optional=True)
