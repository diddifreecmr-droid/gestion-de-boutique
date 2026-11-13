"""`ShopIdentity` : en-tête imprimé sur le reçu (UC-SOC-01 étape 2, UC-SOC-06).

Ville et téléphone obligatoires ; adresse, NIU et RCCM facultatifs. Sorti de `shop.py` (T27)
pour garder l'agrégat sous la limite de taille ; `shop.py` le réexporte.
"""

from dataclasses import dataclass

from app.domain.identity.phone import PhoneNumber
from app.domain.shops.values import clean_optional, clean_text

NIU_MAX_LENGTH = 32


@dataclass(frozen=True, slots=True, kw_only=True)
class ShopIdentity:
    """En-tête imprimé sur le reçu (UC-SOC-01 étape 2) : ville et téléphone obligatoires."""

    name: str
    city: str
    phone: PhoneNumber
    address: str | None = None
    niu: str | None = None
    rccm: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", clean_text(self.name, "name"))
        object.__setattr__(self, "city", clean_text(self.city, "city"))
        if not isinstance(self.phone, PhoneNumber):
            msg = "ShopIdentity.phone doit être un PhoneNumber"
            raise TypeError(msg)
        object.__setattr__(self, "address", clean_optional(self.address, "address"))
        object.__setattr__(self, "niu", clean_optional(self.niu, "niu", max_length=NIU_MAX_LENGTH))
        object.__setattr__(
            self, "rccm", clean_optional(self.rccm, "rccm", max_length=NIU_MAX_LENGTH)
        )

    def header(self) -> dict[str, str | None]:
        """Champs de l'en-tête modifiables par le propriétaire (le nom reste à la console)."""
        return {
            "city": self.city,
            "phone": self.phone.e164,
            "address": self.address,
            "niu": self.niu,
            "rccm": self.rccm,
        }
