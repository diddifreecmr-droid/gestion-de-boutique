"""Agrégat `Alert` : message interne pour un utilisateur d'une boutique (CDC § 20.1).

- **Lue** (`mark_read`) : la pastille ne la compte plus ; l'alerte reste dans la liste.
- **Résolue** (`resolve`) : la condition qui l'a créée a cessé (stock remonté…). Elle reste
  lisible, mais libère sa clé de déduplication.
- **Déduplication** (UC-STK-09 « une seule fois ») : tant qu'une alerte portant `dedup_key`
  n'est pas résolue pour ce destinataire, aucune autre n'est créée avec la même clé.
  `dedup_active_key` vaut `dedup_key` tant que l'alerte est active, `None` une fois résolue :
  c'est la colonne de la contrainte d'unicité (voir l'adaptateur SQL).

L'alerte n'émet aucun événement : elle n'est pas une action de l'utilisateur (RG-T01).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.domain.audit.values import EntityRef, require_text
from app.domain.shared.business_day import require_aware
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import EntityId, ShopId, UserId

DEDUP_KEY_MAX = 200


class AlertId(EntityId):
    __slots__ = ()


class AlertType(StrEnum):
    """Les douze types du CDC § 20.1 (code stable), plus deux alertes exigées par des cas
    d'utilisation sans type au § 20.1 : ajustement du comptable (UC-STK-08, ADJ-03) et
    inventaire validé avec la valeur des écarts (UC-STK-07, INV-04)."""

    LOW_STOCK = "low_stock"  # Stock bas
    STOCK_TO_VERIFY = "stock_to_verify"  # Stock à vérifier
    RECEIVABLE_REMINDER = "receivable_reminder"  # Rappel créance
    TRANSFER_TO_RECEIVE = "transfer_to_receive"  # Déplacement à réceptionner
    RECEPTION_GAP = "reception_gap"  # Écart de réception
    TRIP_EXPENSE_TO_VALIDATE = "trip_expense_to_validate"  # Dépense de voyage à valider
    SALE_ERROR_REPORTED = "sale_error_reported"  # Erreur signalée
    PRICE_REQUEST = "price_request"  # Demande de prix
    BREAKDOWN = "breakdown"  # Panne
    TRUCK_SILENT = "truck_silent"  # Camion sans nouvelle
    DOCUMENT_TO_RENEW = "document_to_renew"  # Document à renouveler
    ENTRY_REFUSED = "entry_refused"  # Saisie refusée
    STOCK_ADJUSTMENT = "stock_adjustment"  # Ajustement de stock (par le comptable)
    INVENTORY_VALIDATED = "inventory_validated"  # Inventaire validé (valeur des écarts)


@dataclass(eq=False, kw_only=True)
class Alert:
    id: AlertId
    shop_id: ShopId
    recipient_id: UserId
    type: AlertType
    entity: EntityRef
    message: str
    created_at: datetime
    dedup_key: str | None = None
    read: bool = False
    resolved_at: datetime | None = None
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.recipient_id, UserId) or not isinstance(self.type, AlertType):
            msg = "Alert exige un UserId destinataire et un AlertType"
            raise TypeError(msg)
        if self.entity.id is None:
            msg = "Une alerte vise un élément identifié (un appui l'ouvre)"
            raise ValueError(msg)
        require_text(self.message, "Alert.message")
        if self.dedup_key is not None and (
            not self.dedup_key.strip() or len(self.dedup_key) > DEDUP_KEY_MAX
        ):
            msg = f"dedup_key : texte non vide de {DEDUP_KEY_MAX} caractères au plus"
            raise ValueError(msg)
        self.created_at = require_aware(self.created_at)

    @classmethod
    def raise_for(
        cls,
        *,
        shop_id: ShopId,
        recipient_id: UserId,
        type: AlertType,
        entity: EntityRef,
        message: str,
        now: datetime,
        dedup_key: str | None = None,
    ) -> "Alert":
        return cls(
            id=AlertId.new(),
            shop_id=shop_id,
            recipient_id=recipient_id,
            type=type,
            entity=entity,
            message=message,
            created_at=now,
            dedup_key=dedup_key,
        )

    @property
    def active(self) -> bool:
        return self.resolved_at is None

    @property
    def dedup_active_key(self) -> str | None:
        """Clé soumise à l'unicité : `dedup_key` tant que l'alerte est active."""
        return self.dedup_key if self.active else None

    def mark_read(self) -> bool:
        """Marque lue ; renvoie `False` si elle l'était déjà (idempotent)."""
        if self.read:
            return False
        self.read = True
        return True

    def resolve(self, now: datetime) -> None:
        """La condition a cessé : libère la clé de déduplication (sans effet si déjà fait)."""
        if self.resolved_at is None:
            self.resolved_at = require_aware(now)
