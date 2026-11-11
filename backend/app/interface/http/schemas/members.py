"""Schémas des membres et de la délégation de l'administrateur (UC-SOC-04, specs § 8.3)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.shared.roles import Role


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MemberResponse(_Strict):
    user_id: str
    name: str
    phone: str
    role: str
    default_location_id: str | None
    active: bool
    """Rattachement actif **dans cette boutique** (RG-D06, portée par boutique)."""
    locked: bool
    must_change_pin: bool
    version: int


class MemberCreateRequest(_Strict):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=32)
    role: Role
    default_location_id: str | None = Field(default=None, max_length=64)


class MemberCreatedResponse(_Strict):
    member: MemberResponse
    temporary_pin: str | None
    """Code provisoire, affiché **une seule fois** ; `null` si le compte existait déjà."""
    existing_account: bool


class MemberPatch(_Strict):
    version: int = Field(ge=1)
    role: Role | None = None
    default_location_id: str | None = Field(default=None, max_length=64)
    active: bool | None = None


class TemporaryPinResponse(_Strict):
    temporary_pin: str


class RevokedDevicesResponse(_Strict):
    revoked_sessions: int


class AdminAccessResponse(_Strict):
    active: bool
    expires_at: datetime | None
