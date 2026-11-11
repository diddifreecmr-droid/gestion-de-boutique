"""Agrégat `Supplier` : fournisseur de la boutique (UC-ACH-02, CDC § 20.3 « Fournisseur »).

- Nom obligatoire, **unique dans la boutique** sans casse ni espaces superflus (contrainte
  `supplier_name`, `Duplicate` 409) ; téléphone, ville, pays, note facultatifs.
- Aucune suppression (RG-T02, aucune route `DELETE`) : un fournisseur, avec ou sans achats,
  ne peut qu'être **désactivé** (`active = False`) ; il garde son historique et sa fiche, mais
  n'est plus proposé pour un nouvel achat.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime

from app.domain.audit.values import EntityRef, Performer, Scalar
from app.domain.purchasing.events import SupplierChanged, SupplierCreated
from app.domain.purchasing.ids import SupplierId
from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId
from app.domain.shops.events import diff
from app.domain.shops.values import clean_optional, clean_text, name_key

NAME_MAX_LENGTH = 120
NOTE_MAX_LENGTH = 500


@dataclass(frozen=True, slots=True, kw_only=True)
class SupplierDetails:
    name: str
    phone: str | None = None
    city: str | None = None
    country: str | None = None
    note: str | None = None
    active: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", clean_text(self.name, "name", max_length=NAME_MAX_LENGTH))
        for name in ("phone", "city", "country"):
            object.__setattr__(self, name, clean_optional(getattr(self, name), name))
        note = clean_optional(self.note, "note", max_length=NOTE_MAX_LENGTH)
        object.__setattr__(self, "note", note)
        if not isinstance(self.active, bool):
            msg = "Oui/Non attendu"
            raise ValidationFailed(msg, details={"field": "active"})

    def scalars(self) -> dict[str, Scalar]:
        return dict(asdict(self))


@dataclass(eq=False, kw_only=True)
class Supplier:
    id: SupplierId
    shop_id: ShopId
    details: SupplierDetails
    created_at: datetime
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.created_at = require_aware(self.created_at)

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
    def entity(self) -> EntityRef:
        return EntityRef("supplier", self.id.value, self.name)

    @classmethod
    def create(
        cls,
        shop_id: ShopId,
        details: SupplierDetails,
        *,
        performer: Performer,
        now: datetime,
        supplier_id: SupplierId | None = None,
    ) -> "Supplier":
        supplier = cls(
            id=supplier_id or SupplierId.new(), shop_id=shop_id, details=details, created_at=now
        )
        supplier.events.record(
            SupplierCreated(
                shop_id=shop_id,
                occurred_at=now,
                performer=performer,
                entity=supplier.entity,
                summary=f"Fournisseur créé : {details.name}",
            )
        )
        return supplier

    def change(self, details: SupplierDetails, *, performer: Performer, now: datetime) -> bool:
        """Nouveaux détails (désactivation comprise) ; `False` si rien ne change."""
        changes = diff(self.details.scalars(), details.scalars())
        if not changes:
            return False
        previous = self.name
        self.details = details
        self.events.record(
            SupplierChanged(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Fournisseur modifié : {previous}",
                changes=changes,
            )
        )
        return True
