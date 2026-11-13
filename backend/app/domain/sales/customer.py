"""Agrégat `Customer` : client de la boutique (UC-VEN-11, CDC § 20.4 « Client »).

- Nom et téléphone obligatoires ; téléphone normalisé en **E.164** par le domaine identité
  (`PhoneNumber.parse` : « 690 00 00 00 » = « +237690000000 », Q-33) et **unique dans la
  boutique** (contrainte `customer_phone`, `DUPLICATE` 409, ERR-DUP-04).
- Type Particulier (défaut) ou Entreprise ; ville, adresse, pièce d'identité (type, numéro,
  photo = pièce jointe facultative), plafond de crédit (≥ 0, absent = aucun contrôle), note.
- `created_by` : qui l'a créé (création rapide depuis une vente comprise) ; il fonde, avec les
  ventes, la portée « ses clients » du vendeur (UC-VEN-11, Q-20).
- Aucune suppression (RG-T02) : un client se modifie, avant/après au journal. Créé par un
  import annulé (QC-6) : **désactivé** (`withdraw`), son téléphone est libéré.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.domain.audit.values import EntityRef, Performer, Scalar
from app.domain.catalog.ids import AttachmentId
from app.domain.catalog.keys import search_key, sort_key
from app.domain.identity.phone import PhoneNumber
from app.domain.sales.events import CustomerChanged, CustomerCreated
from app.domain.sales.ids import CustomerId
from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import InvalidStateTransition
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shops.events import diff
from app.domain.shops.values import clean_optional, clean_text

NAME_MAX_LENGTH = 120
NOTE_MAX_LENGTH = 500


class CustomerKind(StrEnum):
    INDIVIDUAL = "individual"  # Particulier
    COMPANY = "company"  # Entreprise


class IdDocumentType(StrEnum):
    NATIONAL_ID = "national_id"  # CNI
    PASSPORT = "passport"
    DRIVING_LICENSE = "driving_license"  # Permis
    RESIDENCE_PERMIT = "residence_permit"  # Carte de séjour
    OTHER = "other"


@dataclass(frozen=True, slots=True, kw_only=True)
class CustomerDetails:
    name: str
    phone: PhoneNumber
    kind: CustomerKind = CustomerKind.INDIVIDUAL
    city: str | None = None
    address: str | None = None
    id_doc_type: IdDocumentType | None = None
    id_doc_number: str | None = None
    id_doc_photo_id: AttachmentId | None = None
    credit_limit: Money | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", clean_text(self.name, "name", max_length=NAME_MAX_LENGTH))
        if not isinstance(self.phone, PhoneNumber):
            msg = "CustomerDetails.phone doit être un PhoneNumber"
            raise TypeError(msg)
        object.__setattr__(self, "kind", CustomerKind(self.kind))
        for name in ("city", "address", "id_doc_number"):
            object.__setattr__(self, name, clean_optional(getattr(self, name), name))
        if self.id_doc_type is not None:
            object.__setattr__(self, "id_doc_type", IdDocumentType(self.id_doc_type))
        if self.id_doc_photo_id is not None and not isinstance(self.id_doc_photo_id, AttachmentId):
            msg = "CustomerDetails.id_doc_photo_id doit être un AttachmentId"
            raise TypeError(msg)
        if self.credit_limit is not None:
            self.credit_limit.require_non_negative("credit_limit")
        note = clean_optional(self.note, "note", max_length=NOTE_MAX_LENGTH)
        object.__setattr__(self, "note", note)

    def scalars(self) -> dict[str, Scalar]:
        return {
            "name": self.name,
            "phone": self.phone.e164,
            "kind": self.kind.value,
            "city": self.city,
            "address": self.address,
            "id_doc_type": None if self.id_doc_type is None else self.id_doc_type.value,
            "id_doc_number": self.id_doc_number,
            "id_doc_photo_id": None if self.id_doc_photo_id is None else str(self.id_doc_photo_id),
            "credit_limit": None if self.credit_limit is None else self.credit_limit.amount,
            "note": self.note,
        }


@dataclass(eq=False, kw_only=True)
class Customer:
    id: CustomerId
    shop_id: ShopId
    details: CustomerDetails
    created_by: UserId
    created_at: datetime
    released: bool = False
    """Désactivé par l'annulation de son import (QC-6) : téléphone libéré, hors recherche."""
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.created_at = require_aware(self.created_at)

    @property
    def name(self) -> str:
        return self.details.name

    @property
    def phone_key(self) -> str:
        return self.details.phone.e164

    @property
    def unique_phone(self) -> str | None:
        """Téléphone qu'il occupe dans l'unicité `customer_phone` ; aucun une fois libéré."""
        return None if self.released else self.phone_key

    @property
    def search_key(self) -> str:
        """Nom plié + chiffres du téléphone : recherche par nom ou téléphone (UC-VEN-11)."""
        return search_key((self.name, self.details.phone.digits))

    @property
    def sort_key(self) -> str:
        return sort_key(self.name)

    @property
    def entity(self) -> EntityRef:
        return EntityRef("customer", self.id.value, self.name)

    @classmethod
    def create(
        cls,
        shop_id: ShopId,
        details: CustomerDetails,
        *,
        performer: Performer,
        now: datetime,
        customer_id: CustomerId | None = None,
    ) -> "Customer":
        customer = cls(
            id=customer_id or CustomerId.new(),
            shop_id=shop_id,
            details=details,
            created_by=performer.user_id,
            created_at=now,
        )
        customer.events.record(
            CustomerCreated(
                shop_id=shop_id,
                occurred_at=now,
                performer=performer,
                entity=customer.entity,
                summary=f"Client créé : {details.name}",
            )
        )
        return customer

    def withdraw(self, *, performer: Performer, now: datetime) -> None:
        """Annulation de son import (QC-6) : désactivé, téléphone libéré (rien d'effacé)."""
        if self.released:
            msg = "Client déjà désactivé"
            raise InvalidStateTransition(msg, details={"id": str(self.id)})
        self.released = True
        self.events.record(CustomerChanged(
            shop_id=self.shop_id, occurred_at=now, performer=performer, entity=self.entity,
            summary=f"Client désactivé (import annulé) : {self.name}",
            changes=diff({"active": True}, {"active": False}),
        ))  # fmt: skip

    def change(self, details: CustomerDetails, *, performer: Performer, now: datetime) -> bool:
        """Nouveaux détails ; avant/après au journal. `False` si rien ne change."""
        changes = diff(self.details.scalars(), details.scalars())
        if not changes:
            return False
        previous = self.name
        self.details = details
        self.events.record(
            CustomerChanged(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Client modifié : {previous}",
                changes=changes,
            )
        )
        return True
