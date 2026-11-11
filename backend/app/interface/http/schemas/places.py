"""Schémas des lieux et des modes de paiement (`/locations`, `/payment-modes`, specs § 6.3).

Création : `id` (UUIDv7) facultatif fourni par le client → idempotente (même `id` rejoué :
200 et l'élément existant). Modification : `version` obligatoire, champs présents seulement.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.domain.shops.values import LocationKind

ID = Field(default=None, max_length=64)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocationResponse(_Strict):
    id: str
    name: str
    kind: str
    is_point_of_sale: bool
    city: str | None
    display_order: int
    active: bool
    version: int


class LocationListResponse(_Strict):
    items: list[LocationResponse]
    read_only: bool
    """Vrai pour le comptable (« Lecture », CDC § 4.2) et l'administrateur délégué."""


class LocationCreateRequest(_Strict):
    id: str | None = ID
    name: str = Field(min_length=1, max_length=200)
    kind: LocationKind
    is_point_of_sale: bool
    city: str | None = Field(default=None, max_length=1000)
    display_order: int = 0


class LocationPatch(_Strict):
    version: int = Field(ge=1)
    name: str | None = Field(default=None, max_length=200)
    kind: LocationKind | None = None
    is_point_of_sale: bool | None = None
    city: str | None = Field(default=None, max_length=1000)
    display_order: int | None = None
    active: bool | None = None


class PaymentModeResponse(_Strict):
    id: str
    name: str
    reference_required: bool
    active: bool
    display_order: int
    version: int


class PaymentModeCreateRequest(_Strict):
    id: str | None = ID
    name: str = Field(min_length=1, max_length=200)
    reference_required: bool = False
    display_order: int = 0


class PaymentModePatch(_Strict):
    version: int = Field(ge=1)
    name: str | None = Field(default=None, max_length=200)
    reference_required: bool | None = None
    active: bool | None = None
    display_order: int | None = None
