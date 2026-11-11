"""Numéro de châssis vendu : normalisation et réservation par la vente (RG-M01, RG-M02).

**Normalisation (Q-33 tranchée)** : NFKC, majuscules, puis seuls les lettres et chiffres sont
gardés — « lbx 123 », « LBX-123 » et « LBX123 » sont le même châssis (ERR-DUP-02 → 409). La
saisie nettoyée (espaces réduits) est conservée telle quelle pour le reçu (RG-M03).

**Unicité parmi les ventes non annulées** : chaque châssis d'une vente valide est « réservé »
par un `ChassisClaim` dont la clé active (`active_key`) vaut la clé normalisée ; l'annulation de
la vente la **libère** (`active_key = None`, la ligne reste : rien n'est supprimé). La contrainte
d'unicité `sold_chassis_active` porte sur `(shop_id, active_key)` : un `NULL` n'est jamais en
conflit (même procédé que `alert_active_dedup`), ce qui arbitre aussi deux ventes simultanées
du même châssis — la seconde échoue (`Duplicate`), sur toute base et sans index partiel.
"""

import unicodedata
from dataclasses import dataclass, field

from app.domain.sales.ids import ChassisClaimId, SaleId
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId

CHASSIS_MAX_LENGTH = 64


def chassis_key(text: str) -> str:
    """Clé de comparaison d'un châssis ; `ValidationFailed` s'il ne reste aucun caractère."""
    folded = unicodedata.normalize("NFKC", text).upper()
    key = "".join(char for char in folded if char.isalnum())
    if not key:
        msg = "Numéro de châssis sans lettre ni chiffre"
        raise ValidationFailed(msg, details={"field": "chassis_number"})
    return key


@dataclass(eq=False, kw_only=True)
class ChassisClaim:
    id: ChassisClaimId
    shop_id: ShopId
    key: str
    value: str
    sale_id: SaleId
    sale_number: str
    active: bool = True
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    @property
    def active_key(self) -> str | None:
        return self.key if self.active else None

    @classmethod
    def claim(
        cls, shop_id: ShopId, value: str, sale_id: SaleId, sale_number: str
    ) -> "ChassisClaim":
        return cls(
            id=ChassisClaimId.new(),
            shop_id=shop_id,
            key=chassis_key(value),
            value=value,
            sale_id=sale_id,
            sale_number=sale_number,
        )

    def release(self) -> None:
        """Vente annulée ou châssis remplacé par une modification : le numéro redevient libre."""
        if not self.active:
            msg = f"Châssis {self.value} déjà libéré"
            raise ValueError(msg)
        self.active = False
