"""Registre des profils : `profile_for(code)` ; un code inconnu lève `UnknownProfile` (400)."""

from collections.abc import Mapping
from types import MappingProxyType

from app.domain.profiles.apparel import APPAREL, TEXTILE
from app.domain.profiles.motos import MOTOS
from app.domain.profiles.profile import ProfileCode, ShopProfile
from app.domain.shops.errors import UnknownProfile

PROFILES: Mapping[ProfileCode, ShopProfile] = MappingProxyType(
    {profile.code: profile for profile in (MOTOS, APPAREL, TEXTILE)}
)


def profile_for(code: str) -> ShopProfile:
    """Profil du code `code` (valeur de `ProfileCode`) ; `UnknownProfile` sinon."""
    if not isinstance(code, str):
        msg = f"Un code de profil est un str, reçu {type(code).__name__}"
        raise TypeError(msg)
    try:
        profile_code = ProfileCode(code)
    except ValueError as exc:
        raise UnknownProfile(code) from exc
    return PROFILES[profile_code]
