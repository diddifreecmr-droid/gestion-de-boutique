"""Schémas des routes `/auth/*` et `/me` (specs § 6.3).

Le format du code (6 chiffres) et la politique des secrets sont contrôlés par le domaine, pas
ici : un mot de passe admin passe par les mêmes champs. Les bornes ci-dessous ne servent qu'à
refuser tôt une saisie absurde (au plus 128 caractères, plafond du mot de passe).
"""

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.identity.credentials import PASSWORD_MAX_LENGTH

SECRET_FIELD = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LoginRequest(_Strict):
    """Code à 6 chiffres (membre) **ou** mot de passe (administrateur plateforme)."""

    phone: str = Field(min_length=1, max_length=32)
    pin: str | None = Field(default=None, min_length=1, max_length=PASSWORD_MAX_LENGTH)
    password: str | None = Field(default=None, min_length=1, max_length=PASSWORD_MAX_LENGTH)
    device_label: str = Field(min_length=1, max_length=100, examples=["Android — Chrome"])

    @model_validator(mode="after")
    def _exactly_one_secret(self) -> Self:
        if (self.pin is None) == (self.password is None):
            msg = "Fournir soit `pin`, soit `password`"
            raise ValueError(msg)
        return self


class TokenResponse(_Strict):
    """Jeton d'accès (gardé en mémoire par le client, § 7.2) ; le refresh part en cookie."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    must_change_pin: bool


class ChangePinRequest(_Strict):
    """Pour l'administrateur plateforme, ces champs portent le mot de passe."""

    current_pin: str = SECRET_FIELD
    new_pin: str = SECRET_FIELD
    new_pin_confirmation: str = SECRET_FIELD


class ShopMembershipResponse(_Strict):
    shop_id: str
    shop_name: str
    role: str


class MeResponse(_Strict):
    user_id: str
    name: str
    phone: str
    is_platform_admin: bool
    must_change_pin: bool
    shops: list[ShopMembershipResponse]
