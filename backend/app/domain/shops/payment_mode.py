"""Agrégat `PaymentMode` : mode de paiement proposé à la saisie (CDC § 20.1, RG-T19, SET-03).

L'application n'encaisse rien : le mode qualifie un paiement noté. `reference_required` propose
le champ « référence » (jamais obligatoire). Nom unique dans la boutique (sans casse). Un mode
retiré est désactivé, jamais supprimé (les paiements passés le gardent).
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime

from app.domain.audit.values import EntityRef, Performer, Scalar
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId
from app.domain.shops.events import PaymentModeChanged, PaymentModeCreated, diff
from app.domain.shops.ids import PaymentModeId
from app.domain.shops.location import MAX_DISPLAY_ORDER
from app.domain.shops.values import clean_text, name_key, require_int

PAYMENT_MODE_NAME_MAX_LENGTH = 60


@dataclass(frozen=True, slots=True, kw_only=True)
class PaymentModeDetails:
    name: str
    reference_required: bool
    active: bool = True
    display_order: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "name", clean_text(self.name, "name", max_length=PAYMENT_MODE_NAME_MAX_LENGTH)
        )
        require_int(self.display_order, "display_order", low=0, high=MAX_DISPLAY_ORDER)
        if not isinstance(self.reference_required, bool) or not isinstance(self.active, bool):
            msg = "PaymentModeDetails : reference_required et active sont des booléens"
            raise TypeError(msg)

    def scalars(self) -> dict[str, Scalar]:
        return asdict(self)


@dataclass(eq=False, kw_only=True)
class PaymentMode:
    id: PaymentModeId
    shop_id: ShopId
    details: PaymentModeDetails
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    @property
    def name(self) -> str:
        return self.details.name

    @property
    def name_key(self) -> str:
        return name_key(self.details.name)

    @property
    def entity(self) -> EntityRef:
        return EntityRef("payment_mode", self.id.value, self.name)

    @classmethod
    def seed(cls, shop_id: ShopId, details: PaymentModeDetails) -> "PaymentMode":
        """Mode de départ du profil (aucun événement : `ShopOpened` suffit)."""
        return cls(id=PaymentModeId.new(), shop_id=shop_id, details=details)

    @classmethod
    def create(
        cls,
        shop_id: ShopId,
        details: PaymentModeDetails,
        *,
        performer: Performer,
        now: datetime,
        mode_id: PaymentModeId | None = None,
    ) -> "PaymentMode":
        mode = cls(id=mode_id or PaymentModeId.new(), shop_id=shop_id, details=details)
        mode.events.record(
            PaymentModeCreated(
                shop_id=shop_id,
                occurred_at=now,
                performer=performer,
                entity=mode.entity,
                summary=f"Mode de paiement ajouté : {details.name}",
            )
        )
        return mode

    def change(self, details: PaymentModeDetails, *, performer: Performer, now: datetime) -> bool:
        changes = diff(self.details.scalars(), details.scalars())
        if not changes:
            return False
        self.details = details
        self.events.record(
            PaymentModeChanged(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Mode de paiement modifié : {details.name}",
                changes=changes,
            )
        )
        return True
