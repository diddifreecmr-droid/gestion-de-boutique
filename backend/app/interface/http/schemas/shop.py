"""Schémas du profil et des réglages d'une boutique (`/shops/{id}/profile`, `/settings`).

`SettingsPatch` : modification partielle, seuls les champs **présents** changent (un champ
facultatif à `null` est effacé) ; `version` obligatoire (409 si l'objet a changé).
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.profiles.printing import ReceiptFormat


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RoleResponse(_Strict):
    code: str
    label: str


class MenuEntryResponse(_Strict):
    code: str
    label: str
    module: str
    children: list["MenuEntryResponse"]


class FieldResponse(_Strict):
    code: str
    label: str
    kind: str
    required: bool
    unique: bool
    choices: list[str]


class ShopHeaderResponse(_Strict):
    name: str
    city: str
    phone: str
    address: str | None
    niu: str | None
    rccm: str | None


class ReceiptSettingsResponse(_Strict):
    format: str
    print_profile: str
    paper_width_mm: int
    printable_width_mm: int
    margin_mm: int
    font_size_pt: int
    show_logo: bool
    copies: int
    footer_message: str | None
    header: ShopHeaderResponse


class ProfileResponse(_Strict):
    shop_id: str
    profile_code: str
    profile_version: int
    profile_label: str
    enabled_modules: list[str]
    roles: list[RoleResponse]
    role: str | None
    role_label: str | None
    menu: list[MenuEntryResponse]
    article_fields: list[FieldResponse]
    sale_fields: list[FieldResponse]
    stock_units: list[str]
    receipt: ReceiptSettingsResponse
    min_price_enabled: bool
    min_price_requires_approval: bool
    default_location_id: str | None
    entitlements: dict[str, bool]
    """Droits d'offre de la boutique (TR-26) : `{"offline_capture": false}` en V1. Le frontend
    n'utilise la file d'envoi hors connexion que si `offline_capture` est vrai (T23)."""


class SettingsResponse(_Strict):
    version: int
    receipt_format: str
    print_profile: str
    paper_width_mm: int
    printable_width_mm: int
    margin_mm: int
    font_size_pt: int
    show_logo: bool
    footer_message: str | None
    copies: int
    low_stock_threshold: str
    min_price_enabled: bool
    min_price_requires_approval: bool
    exchange_days: int | None
    truck_silent_hours: int | None
    transfer_in_transit_days: int | None
    reception_location_id: str | None
    header: ShopHeaderResponse


class SettingsPatch(_Strict):
    version: int = Field(ge=1)
    receipt_format: ReceiptFormat | None = None
    paper_width_mm: int | None = None
    printable_width_mm: int | None = None
    margin_mm: int | None = None
    font_size_pt: int | None = None
    show_logo: bool | None = None
    footer_message: str | None = Field(default=None, max_length=1000)
    copies: int | None = None
    low_stock_threshold: Decimal | None = None
    min_price_enabled: bool | None = None
    min_price_requires_approval: bool | None = None
    exchange_days: int | None = None
    truck_silent_hours: int | None = None
    transfer_in_transit_days: int | None = None
    reception_location_id: str | None = Field(default=None, max_length=64)
    city: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=1000)
    niu: str | None = Field(default=None, max_length=100)
    rccm: str | None = Field(default=None, max_length=100)
