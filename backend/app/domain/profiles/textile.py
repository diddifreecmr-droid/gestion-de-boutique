"""Profil Textile : raccourcis de longueur à la vente (RG-X05, UC-TEX-01, T31).

CDC § 19.3 : « pièce complète (6 yards), demi-pièce (3 yards), 1 m, 2 m, 3 m ». Servis par
`GET /profile` (`sale_shortcuts`, vide pour les autres profils) dans cet ordre ; le client les
applique à l'article choisi selon `resolve_shortcut`, seule règle de calcul :

- « Pièce complète » : article vendu à la pièce → « à la pièce », 1 pièce (le stock retire sa
  longueur au dixième, RG-X01) ; sinon au mètre, la longueur de la pièce au dixième ;
- « Demi-pièce » : au mètre, la moitié de la longueur de la pièce, au dixième ;
- « 1 m », « 2 m », « 3 m » : au mètre.

Longueur de la pièce : celle de l'article, sinon 6 yards (5,4864 m, RG-X02). Arrondi au
dixième, demi vers le haut, comme toute conversion (QC-3 : stock au dixième) : pièce de
5,49 m → demi-pièce **2,7 m** (2,745) ; 6 yards → 5,5 m, 3 yards → 2,7 m.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from types import MappingProxyType

from app.domain.profiles.profile import ProfileCode
from app.domain.sales.lines import SaleMode
from app.domain.shared.quantity import METERS_PER_YARD, TENTH

PIECE_YARDS = Decimal(6)
"""Longueur d'une pièce de pagne sans longueur renseignée (CDC § 19.3 : 6 yards)."""


class ShortcutBasis(StrEnum):
    PIECE = "piece"  # pièce complète
    HALF_PIECE = "half_piece"  # demi-pièce
    LENGTH = "length"  # longueur fixe en mètres


@dataclass(frozen=True, slots=True)
class SaleShortcut:
    code: str
    label: str
    basis: ShortcutBasis
    length_m: Decimal | None = None
    """Longueur fixe (`LENGTH` seulement), au dixième."""

    def __post_init__(self) -> None:
        if (self.basis is ShortcutBasis.LENGTH) != (self.length_m is not None):
            msg = f"Raccourci {self.code} : longueur fixe pour « length » seulement"
            raise ValueError(msg)
        if self.length_m is not None and self.length_m != self.length_m.quantize(TENTH):
            msg = f"Raccourci {self.code} : longueur au dixième"
            raise ValueError(msg)

    @property
    def yards(self) -> Decimal | None:
        """Longueur de référence du CDC (6 ou 3 yards) pour une pièce sans longueur."""
        if self.basis is ShortcutBasis.LENGTH:
            return None
        return PIECE_YARDS if self.basis is ShortcutBasis.PIECE else PIECE_YARDS / 2


@dataclass(frozen=True, slots=True)
class ResolvedShortcut:
    sale_mode: SaleMode
    quantity: Decimal
    """Pièces (« à la pièce ») ou mètres au dixième (« au mètre »)."""


def _tenth(value: Decimal) -> Decimal:
    return value.quantize(TENTH, rounding=ROUND_HALF_UP)


def resolve_shortcut(
    shortcut: SaleShortcut, *, piece_length_m: Decimal | None, sold_by_piece: bool
) -> ResolvedShortcut:
    """Mode et quantité à saisir pour un article (voir le tableau du module)."""
    if shortcut.length_m is not None:
        return ResolvedShortcut(SaleMode.METER, shortcut.length_m)
    piece = piece_length_m if piece_length_m is not None else PIECE_YARDS * METERS_PER_YARD
    if shortcut.basis is ShortcutBasis.PIECE:
        if sold_by_piece and piece_length_m is not None:
            return ResolvedShortcut(SaleMode.PIECE, Decimal(1))
        return ResolvedShortcut(SaleMode.METER, _tenth(piece))
    return ResolvedShortcut(SaleMode.METER, _tenth(piece / 2))


TEXTILE_SHORTCUTS = (
    SaleShortcut("piece", "Pièce complète", ShortcutBasis.PIECE),
    SaleShortcut("half_piece", "Demi-pièce", ShortcutBasis.HALF_PIECE),
    SaleShortcut("1m", "1 m", ShortcutBasis.LENGTH, Decimal(1)),
    SaleShortcut("2m", "2 m", ShortcutBasis.LENGTH, Decimal(2)),
    SaleShortcut("3m", "3 m", ShortcutBasis.LENGTH, Decimal(3)),
)

SALE_SHORTCUTS: Mapping[ProfileCode, tuple[SaleShortcut, ...]] = MappingProxyType(
    {ProfileCode.MOTOS: (), ProfileCode.APPAREL: (), ProfileCode.TEXTILE: TEXTILE_SHORTCUTS}
)
if set(SALE_SHORTCUTS) != set(ProfileCode):  # tout nouveau profil déclare ses raccourcis
    _msg = f"Raccourcis de vente non déclarés pour {sorted(set(ProfileCode) - set(SALE_SHORTCUTS))}"
    raise RuntimeError(_msg)


def shortcuts_for(code: ProfileCode) -> tuple[SaleShortcut, ...]:
    return SALE_SHORTCUTS[ProfileCode(code)]
