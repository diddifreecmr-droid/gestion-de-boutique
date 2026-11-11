"""Agrégat `ShopSettings` : réglages de la boutique (CDC § 20.1, UC-SOC-06, specs § 9.1).

Un seul jeu par boutique. `SettingsValues` est immuable et validé à la construction (bornes du
CDC : 1 à 3 exemplaires, pied de reçu de 200 caractères, seuil décimal ≥ 0…) ; une saisie hors
bornes lève `ValidationFailed` (400) en nommant le champ. `change` inscrit **chaque** champ
modifié au journal avec son avant/après (SET-01).
"""

from dataclasses import dataclass, field, fields
from datetime import datetime
from decimal import Decimal

from app.domain.audit.values import EntityRef, Performer, Scalar
from app.domain.profiles.printing import PrintLayout, ReceiptFormat
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import EntityId, ShopId
from app.domain.shops.events import SettingsChanged, diff
from app.domain.shops.ids import LocationId, ShopSettingsId
from app.domain.shops.values import clean_optional, require_int

FOOTER_MAX_LENGTH = 200
COPIES_RANGE = (1, 3)
THRESHOLD_MAX = Decimal(1_000_000)
TENTH = Decimal("0.1")
_OPTIONAL_BOUNDS = {
    "exchange_days": (0, 365),
    "truck_silent_hours": (1, 720),
    "transfer_in_transit_days": (1, 365),
}


def _threshold(value: object) -> Decimal:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or not 0 <= value < THRESHOLD_MAX
        or value != value.quantize(TENTH)
    ):
        msg = "Seuil décimal ≥ 0, au dixième près"
        raise ValidationFailed(msg, details={"field": "low_stock_threshold"})
    return value.quantize(TENTH)


@dataclass(frozen=True, slots=True, kw_only=True)
class SettingsValues:
    receipt_format: ReceiptFormat
    paper_width_mm: int
    printable_width_mm: int
    margin_mm: int
    font_size_pt: int
    show_logo: bool
    footer_message: str | None = None
    copies: int = 1
    low_stock_threshold: Decimal = Decimal(2)
    min_price_enabled: bool = False
    exchange_days: int | None = None
    truck_silent_hours: int | None = None
    transfer_in_transit_days: int | None = 7
    reception_location_id: LocationId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "receipt_format", ReceiptFormat(self.receipt_format))
        self.layout()  # valide largeurs, marge, taille du texte, logo
        footer = clean_optional(self.footer_message, "footer_message", max_length=FOOTER_MAX_LENGTH)
        object.__setattr__(self, "footer_message", footer)
        require_int(self.copies, "copies", low=COPIES_RANGE[0], high=COPIES_RANGE[1])
        object.__setattr__(self, "low_stock_threshold", _threshold(self.low_stock_threshold))
        if not isinstance(self.min_price_enabled, bool):
            msg = "Oui/Non attendu"
            raise ValidationFailed(msg, details={"field": "min_price_enabled"})
        for name, (low, high) in _OPTIONAL_BOUNDS.items():
            value = getattr(self, name)
            if value is not None:
                require_int(value, name, low=low, high=high)
        location = self.reception_location_id
        if location is not None and not isinstance(location, LocationId):
            msg = "reception_location_id doit être un LocationId"
            raise TypeError(msg)

    def layout(self) -> PrintLayout:
        return PrintLayout(
            self.paper_width_mm,
            self.printable_width_mm,
            self.margin_mm,
            self.font_size_pt,
            self.show_logo,
        )

    def scalars(self) -> dict[str, Scalar]:
        values: dict[str, Scalar] = {}
        for item in fields(self):
            value = getattr(self, item.name)
            if isinstance(value, Decimal | EntityId):
                value = str(value)
            elif isinstance(value, ReceiptFormat):
                value = value.value
            values[item.name] = value
        return values


@dataclass(eq=False, kw_only=True)
class ShopSettings:
    id: ShopSettingsId
    shop_id: ShopId
    values: SettingsValues
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    @property
    def entity(self) -> EntityRef:
        return EntityRef("shop_settings", self.id.value)

    @classmethod
    def seed(cls, shop_id: ShopId, values: SettingsValues) -> "ShopSettings":
        return cls(id=ShopSettingsId.new(), shop_id=shop_id, values=values)

    def change(self, values: SettingsValues, *, performer: Performer, now: datetime) -> bool:
        """Nouveaux réglages ; un événement porte tous les changements. `False` si aucun."""
        changes = diff(self.values.scalars(), values.scalars())
        if not changes:
            return False
        self.values = values
        self.events.record(
            SettingsChanged(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary="Réglages modifiés : " + ", ".join(c.field for c in changes),
                changes=changes,
            )
        )
        return True
