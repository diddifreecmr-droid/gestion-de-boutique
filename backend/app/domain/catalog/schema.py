"""Champs d'article **propres au profil**, validés par le schéma du profil (specs § 4.5).

Le profil (`ShopProfile.article_fields`) décrit les champs ; ce module les lit et les valide :
champ inconnu, champ obligatoire manquant ou valeur du mauvais type → `ValidationFailed` qui
nomme le champ. Les champs à rôle particulier sont **promus** (colonnes dédiées) ; les autres
(cylindrée, catégorie, type…) vont dans `attributes`, un dictionnaire de scalaires JSON.

| Champ promu | Rôle |
| --- | --- |
| `name` | nom saisi ; absent du profil → nom calculé « Marque Modèle » (Motos, CDC § 17.2) |
| `brand`, `model` | marque + modèle unique dans la boutique quand le profil a `model` |
| `reference` | référence unique, générée si vide (Prêt-à-porter, Textile) |
| `unit` | unité de stock au choix (Textile) ; sinon l'unique unité du profil |
| `sold_by_piece`, `piece_length_m` | vente à la pièce et longueur d'une pièce (Textile) |
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from app.domain.audit.values import Scalar
from app.domain.catalog.keys import fold
from app.domain.profiles.fields import FieldKind, FieldSpec
from app.domain.profiles.profile import ShopProfile
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.quantity import StockUnit
from app.domain.shops.values import clean_optional, clean_text

PROMOTED = frozenset(
    {"name", "brand", "model", "reference", "unit", "sold_by_piece", "piece_length_m"}
)
TEXT_MAX_LENGTH = 120
INTEGER_MAX = 1_000_000
PIECE_LENGTH_MAX = Decimal(1000)
HUNDREDTH = Decimal("0.01")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileFields:
    """Champs du profil, validés ; `display_name` est calculé ou saisi."""

    display_name: str
    brand: str | None = None
    model: str | None = None
    reference: str | None = None
    stock_unit: StockUnit
    sold_by_piece: bool = False
    piece_length_m: Decimal | None = None
    attributes: dict[str, Scalar] = field(default_factory=dict)


def _invalid(code: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, details={"field": code})


def _text(spec: FieldSpec, value: object) -> str | None:
    if spec.required:
        text: str | None = clean_text(value, spec.code, max_length=TEXT_MAX_LENGTH)
    else:
        text = clean_optional(value, spec.code, max_length=TEXT_MAX_LENGTH)
    if text is not None and not fold(text):
        raise _invalid(spec.code, "Au moins une lettre ou un chiffre attendu")
    return text


def _decimal(code: str, value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, int | str | Decimal):
        raise _invalid(code, "Nombre décimal attendu (chaîne « 5.49 » ou entier)")
    try:
        number = Decimal(value.strip() if isinstance(value, str) else value)
    except InvalidOperation as exc:
        raise _invalid(code, "Nombre décimal illisible") from exc
    if not number.is_finite() or number != number.quantize(HUNDREDTH):
        raise _invalid(code, "Nombre décimal au centième près attendu")
    return number.quantize(HUNDREDTH)


def _value(spec: FieldSpec, value: object) -> Scalar | Decimal:
    """Valeur validée selon le type déclaré du champ (`None` = non renseigné)."""
    if spec.kind is FieldKind.TEXT:
        return _text(spec, value)
    if value is None:
        return None
    if spec.kind is FieldKind.INTEGER:
        if isinstance(value, bool) or not isinstance(value, int) or not 0 < value < INTEGER_MAX:
            raise _invalid(spec.code, f"Entier entre 1 et {INTEGER_MAX - 1} attendu")
        return value
    if spec.kind is FieldKind.BOOLEAN:
        if not isinstance(value, bool):
            raise _invalid(spec.code, "Oui/Non attendu")
        return value
    if spec.kind is FieldKind.CHOICE:
        if value not in spec.choices:
            msg = "Choix inconnu"
            raise ValidationFailed(msg, details={"field": spec.code, "choices": list(spec.choices)})
        return str(value)
    return _decimal(spec.code, value)


def read_profile_fields(profile: ShopProfile, values: Mapping[str, object]) -> ProfileFields:
    """Valide `values` (code de champ → valeur) contre les champs d'article du profil."""
    specs = {spec.code: spec for spec in profile.article_fields}
    unknown = sorted(set(values) - set(specs))
    if unknown:
        msg = "Champ inconnu pour ce type de boutique"
        raise ValidationFailed(msg, details={"fields": unknown})
    read = {code: _value(spec, values.get(code)) for code, spec in specs.items()}
    missing = sorted(code for code, spec in specs.items() if spec.required and read[code] is None)
    if missing:
        msg = "Champ obligatoire"
        raise ValidationFailed(msg, details={"fields": missing})
    return _assemble(profile, read)


def _assemble(profile: ShopProfile, read: Mapping[str, Scalar | Decimal]) -> ProfileFields:
    def text(code: str) -> str | None:
        value = read.get(code)
        return value if isinstance(value, str) else None

    chosen = text("unit")
    unit = profile.stock_units[0] if chosen is None else StockUnit(chosen)
    sold_by_piece = read.get("sold_by_piece") is True
    length = read.get("piece_length_m")
    piece_length = length if isinstance(length, Decimal) else None
    if sold_by_piece and unit is not StockUnit.METER:
        raise _invalid("sold_by_piece", "Vente à la pièce possible si l'unité est le mètre")
    if sold_by_piece != (piece_length is not None):
        raise _invalid("piece_length_m", "Longueur de la pièce exigée avec la vente à la pièce")
    if piece_length is not None and not 0 < piece_length < PIECE_LENGTH_MAX:
        raise _invalid("piece_length_m", "Longueur de pièce strictement positive attendue")
    brand, model, name = text("brand"), text("model"), text("name")
    display = name if "name" in read else " ".join(p for p in (brand, model) if p)
    if not display:
        msg = f"Profil {profile.code} : ni nom ni marque + modèle pour nommer l'article"
        raise ValueError(msg)
    attributes: dict[str, Scalar] = {
        code: str(value) if isinstance(value, Decimal) else value
        for code, value in read.items()
        if code not in PROMOTED and value is not None
    }
    return ProfileFields(
        display_name=display,
        brand=brand,
        model=model,
        reference=text("reference"),
        stock_unit=unit,
        sold_by_piece=sold_by_piece,
        piece_length_m=piece_length,
        attributes=attributes,
    )
