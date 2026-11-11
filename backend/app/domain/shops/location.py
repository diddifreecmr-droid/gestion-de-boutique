"""Agrégat `Location` : boutique ou entrepôt où du stock est gardé (CDC § 20.1, UC-SOC-05).

- Nom obligatoire, **unique dans la boutique** sans tenir compte de la casse (`name_key`).
- Les règles qui regardent les autres lieux ou le stock (dernier point de vente, lieu qui a du
  stock, lieu habituel d'un vendeur) sont vérifiées par le cas d'utilisation `ManageLocations`,
  qui seul voit l'ensemble.
- Les lieux de départ du profil sont créés sans événement : l'ouverture de la boutique est
  journalisée une fois (`ShopOpened`).
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime

from app.domain.audit.values import EntityRef, Performer, Scalar
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId
from app.domain.shops.events import LocationChanged, LocationCreated, diff
from app.domain.shops.ids import LocationId
from app.domain.shops.values import LocationKind, clean_optional, clean_text, name_key, require_int

MAX_DISPLAY_ORDER = 999


@dataclass(frozen=True, slots=True, kw_only=True)
class LocationDetails:
    name: str
    kind: LocationKind
    is_point_of_sale: bool
    city: str | None = None
    display_order: int = 0
    active: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", clean_text(self.name, "name"))
        object.__setattr__(self, "kind", LocationKind(self.kind))
        object.__setattr__(self, "city", clean_optional(self.city, "city"))
        require_int(self.display_order, "display_order", low=0, high=MAX_DISPLAY_ORDER)
        for name in ("is_point_of_sale", "active"):
            if not isinstance(getattr(self, name), bool):
                msg = f"LocationDetails.{name} doit être un booléen"
                raise TypeError(msg)

    def scalars(self) -> dict[str, Scalar]:
        values = asdict(self)
        values["kind"] = self.kind.value
        return values


@dataclass(eq=False, kw_only=True)
class Location:
    id: LocationId
    shop_id: ShopId
    details: LocationDetails
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    @property
    def name(self) -> str:
        return self.details.name

    @property
    def name_key(self) -> str:
        return name_key(self.details.name)

    @property
    def active(self) -> bool:
        return self.details.active

    @property
    def is_active_point_of_sale(self) -> bool:
        return self.details.active and self.details.is_point_of_sale

    @property
    def entity(self) -> EntityRef:
        return EntityRef("location", self.id.value, self.name)

    @classmethod
    def seed(cls, shop_id: ShopId, details: LocationDetails) -> "Location":
        """Lieu de départ du profil (aucun événement)."""
        return cls(id=LocationId.new(), shop_id=shop_id, details=details)

    @classmethod
    def create(
        cls,
        shop_id: ShopId,
        details: LocationDetails,
        *,
        performer: Performer,
        now: datetime,
        location_id: LocationId | None = None,
    ) -> "Location":
        location = cls(id=location_id or LocationId.new(), shop_id=shop_id, details=details)
        location.events.record(
            LocationCreated(
                shop_id=shop_id,
                occurred_at=now,
                performer=performer,
                entity=location.entity,
                summary=f"Lieu créé : {details.name}",
            )
        )
        return location

    def change(self, details: LocationDetails, *, performer: Performer, now: datetime) -> bool:
        """Remplace les détails ; journalise l'avant/après. `False` si rien ne change."""
        changes = diff(self.details.scalars(), details.scalars())
        if not changes:
            return False
        self.details = details
        self.events.record(
            LocationChanged(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Lieu modifié : {details.name}",
                changes=changes,
            )
        )
        return True
