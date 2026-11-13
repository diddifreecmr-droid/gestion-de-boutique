"""Agrégat `Adjustment` : correction ponctuelle du stock (UC-STK-08, CDC § 20.2 « Ajustement »).

- Sens + ou -, quantité **strictement positive** dans l'unité de stock (RG-T08 : 1,5 moto
  refusée), état Vendable ou Abîmé.
- Motif dans la liste du CDC ; « Autre » exige une note (ADJ-02). Photo : identifiant de pièce
  jointe facultatif (TR-17). « Chute » (RG-X06, UC-TEX-03) : sortie seulement, mouvement
  « Chute » ; la longueur est la quantité (au dixième de mètre pour un tissu). Le CDC ne prévoit **pas de numéro** d'ajustement.
- Un écart d'inventaire crée aussi un ajustement (`inventory_id` renseigné, motif
  `INVENTORY_GAP`, note = motif saisi pour l'écart) ; ce motif n'est pas proposé à la saisie.
- L'ajustement est figé dès sa création (il ne se corrige que par un nouvel ajustement) ;
  le mouvement qu'il cause est posté par le grand livre dans la même transaction.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.domain.audit.values import EntityRef, Performer
from app.domain.catalog.ids import ArticleId, AttachmentId
from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.quantity import Quantity
from app.domain.shops.ids import LocationId
from app.domain.shops.values import clean_optional
from app.domain.stock.events import AdjustmentRecorded
from app.domain.stock.ids import AdjustmentId, InventoryId
from app.domain.stock.values import MovementType, StockCondition

NOTE_MAX_LENGTH = 500


class AdjustmentDirection(StrEnum):
    IN = "in"  # +
    OUT = "out"  # -


class AdjustmentReason(StrEnum):
    BREAKAGE = "breakage"  # Casse
    THEFT = "theft"  # Vol
    LOSS = "loss"  # Perte
    ENTRY_ERROR = "entry_error"  # Erreur de saisie
    SAMPLE_OR_GIFT = "sample_or_gift"  # Échantillon ou cadeau
    SUPPLIER_RETURN = "supplier_return"  # Retour au fournisseur
    OFFCUT = "offcut"  # Chute (RG-X06)
    OTHER = "other"  # Autre (note obligatoire)
    INVENTORY_GAP = "inventory_gap"  # Écart d'inventaire (créé par la validation)


MANUAL_REASONS = frozenset(AdjustmentReason) - {AdjustmentReason.INVENTORY_GAP}


@dataclass(frozen=True, slots=True, kw_only=True)
class AdjustmentDraft:
    """Saisie d'un ajustement (validée par `Adjustment`)."""

    location_id: LocationId
    article_id: ArticleId
    direction: AdjustmentDirection
    quantity: Quantity
    condition: StockCondition
    reason: AdjustmentReason
    note: str | None = None
    photo_id: AttachmentId | None = None
    inventory_id: InventoryId | None = None
    adjustment_id: AdjustmentId | None = None


@dataclass(eq=False, kw_only=True)
class Adjustment:
    id: AdjustmentId
    shop_id: ShopId
    location_id: LocationId
    article_id: ArticleId
    direction: AdjustmentDirection
    quantity: Quantity
    condition: StockCondition
    reason: AdjustmentReason
    created_at: datetime
    author_id: UserId
    note: str | None = None
    photo_id: AttachmentId | None = None
    inventory_id: InventoryId | None = None
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.direction = AdjustmentDirection(self.direction)
        self.condition = StockCondition(self.condition)
        self.reason = AdjustmentReason(self.reason)
        self.quantity.require_positive("quantity")
        self.note = clean_optional(self.note, "note", max_length=NOTE_MAX_LENGTH)
        needs_note = self.reason in (AdjustmentReason.OTHER, AdjustmentReason.INVENTORY_GAP)
        if needs_note and not self.note:
            msg = "Une note est obligatoire pour ce motif"
            raise ValidationFailed(msg, details={"field": "note"})
        if self.reason is AdjustmentReason.OFFCUT and self.direction is AdjustmentDirection.IN:
            msg = "Une chute sort du stock : sens « - » seulement (RG-X06)"
            raise ValidationFailed(msg, details={"field": "direction"})
        if (self.reason is AdjustmentReason.INVENTORY_GAP) != (self.inventory_id is not None):
            msg = "Le motif « écart d'inventaire » est réservé aux inventaires"
            raise ValidationFailed(msg, details={"field": "reason"})
        self.created_at = require_aware(self.created_at)

    @property
    def movement_type(self) -> MovementType:
        if self.direction is AdjustmentDirection.IN:
            return MovementType.ADJUSTMENT_IN
        if self.reason is AdjustmentReason.OFFCUT:
            return MovementType.OFFCUT
        return MovementType.ADJUSTMENT_OUT

    @property
    def signed_quantity(self) -> Quantity:
        return self.quantity if self.direction is AdjustmentDirection.IN else -self.quantity

    @property
    def entity(self) -> EntityRef:
        return EntityRef("adjustment", self.id.value)

    @classmethod
    def record(
        cls,
        draft: "AdjustmentDraft",
        *,
        shop_id: ShopId,
        performer: Performer,
        now: datetime,
        article_name: str,
    ) -> "Adjustment":
        """Nouvel ajustement + événement journalisé « sensible » (le mouvement suit)."""
        adjustment = cls(
            id=draft.adjustment_id or AdjustmentId.new(),
            shop_id=shop_id,
            location_id=draft.location_id,
            article_id=draft.article_id,
            direction=draft.direction,
            quantity=draft.quantity,
            condition=draft.condition,
            reason=draft.reason,
            note=draft.note,
            photo_id=draft.photo_id,
            inventory_id=draft.inventory_id,
            created_at=now,
            author_id=performer.user_id,
        )
        sign = "+" if adjustment.direction is AdjustmentDirection.IN else "-"
        kind = "Chute" if adjustment.reason is AdjustmentReason.OFFCUT else "Ajustement"
        adjustment.events.record(
            AdjustmentRecorded(
                shop_id=shop_id,
                occurred_at=now,
                performer=performer,
                entity=adjustment.entity,
                summary=f"{kind} {sign}{adjustment.quantity} : {article_name}"[:500],
                reason=adjustment.note or adjustment.reason.value,
                from_inventory=adjustment.inventory_id is not None,
            )
        )
        return adjustment
