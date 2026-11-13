"""Colonnes du modèle Articles, tirées des champs d'article du profil (CDC § 15.1, IMP-01).

- Une colonne par champ du profil (Motos : Marque *, Modèle *, Cylindrée, Catégorie ;
  Prêt-à-porter : Nom *, Référence, Catégorie, Type, Marque ; Textile : Nom *, Référence, Type,
  Unité *, Vente à la pièce, Longueur d'une pièce), puis les prix et le seuil d'alerte.
- Prix de vente à la pièce et prix minimum à la pièce : seulement pour un profil qui vend à la
  pièce (champ `sold_by_piece`, Textile).
- `field_value` convertit une cellule nettoyée dans le type du champ du profil (entier, oui/non,
  unité) ; refus → `CellRejected` (message complet, la colonne est nommée par l'appelant).
"""

import unicodedata
from collections.abc import Mapping
from decimal import Decimal
from types import MappingProxyType

from app.domain.imports.columns import ChoiceSource, CleanValue, ColumnKind, ColumnSpec
from app.domain.imports.problems import CellRejected
from app.domain.profiles.fields import FieldKind, FieldSpec
from app.domain.profiles.profile import ShopProfile

PIECE_FIELD = "sold_by_piece"
UNIT_LABELS: Mapping[str, str] = MappingProxyType({"metre": "METER", "piece": "PIECE"})
"""Unité saisie (pliée, sans accent) → code du profil ; le code lui-même est aussi accepté."""
YES = frozenset({"oui", "o", "vrai", "1", "yes"})
NO = frozenset({"non", "n", "faux", "0", "no"})

_SUBJECTS = MappingProxyType(
    {
        "name": "le nom",
        "brand": "la marque",
        "model": "le modèle",
        "engine_cc": "la cylindrée",
        "category": "la catégorie",
        "reference": "la référence",
        "type": "le type",
        "unit": "l'unité",
        "sold_by_piece": "la vente à la pièce",
        "piece_length_m": "la longueur d'une pièce",
    }
)
_HEADERS = MappingProxyType({"piece_length_m": "Longueur d'une pièce (m)"})
_EXAMPLES = MappingProxyType(
    {
        "name": "Chemise lin",
        "brand": "Haojue",
        "model": "HJ125-8",
        "engine_cc": "125",
        "category": "Moto",
        "reference": "",
        "unit": "Mètre",
        "sold_by_piece": "Oui",
        "piece_length_m": "5,49",
    }
)
_HELP = MappingProxyType(
    {
        "reference": "Laissée vide, elle est générée (REF-000001).",
        "unit": "« Mètre » ou « Pièce ».",
        "sold_by_piece": "« Oui » si l'article se vend aussi à la pièce.",
        "piece_length_m": "En mètres, au centième (6 yards = 5,49).",
        "category": "Choisie dans la liste ou nouvelle.",
    }
)


def _amount(key: str, header: str, subject: str, example: str = "") -> ColumnSpec:
    return ColumnSpec(
        key=key, header=header, subject=subject, kind=ColumnKind.AMOUNT, example=example,
        help="FCFA entiers ; réservé au propriétaire.",
    )  # fmt: skip


def _field_column(spec: FieldSpec) -> ColumnSpec:
    numeric = spec.kind in {FieldKind.INTEGER, FieldKind.DECIMAL}
    return ColumnSpec(
        key=spec.code,
        header=_HEADERS.get(spec.code, spec.label),
        subject=_SUBJECTS.get(spec.code, f"« {spec.label} »"),
        kind=ColumnKind.NUMBER if numeric else ColumnKind.TEXT,
        required=spec.required,
        example=_EXAMPLES.get(spec.code, ""),
        help=_HELP.get(spec.code, ""),
        choices=ChoiceSource.CATEGORIES if spec.code == "category" else None,
    )


def sells_by_piece(profile: ShopProfile) -> bool:
    return any(spec.code == PIECE_FIELD for spec in profile.article_fields)


def article_columns(profile: ShopProfile) -> tuple[ColumnSpec, ...]:
    columns = [_field_column(spec) for spec in profile.article_fields]
    columns.append(_amount("base_price", "Prix de vente", "le prix de vente", "9 000"))
    columns.append(_amount("min_price", "Prix minimum", "le prix minimum"))
    if sells_by_piece(profile):
        columns.append(_amount("base_price_piece", "Prix à la pièce", "le prix à la pièce"))
        columns.append(_amount("min_price_piece", "Minimum à la pièce", "le minimum à la pièce"))
    columns.append(
        ColumnSpec(
            key="alert_threshold",
            header="Seuil d'alerte",
            subject="le seuil d'alerte",
            kind=ColumnKind.NUMBER,
            help="Stock bas en dessous de ce nombre (facultatif).",
        )
    )
    return tuple(columns)


def _fold(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return plain.strip().casefold()


def field_value(spec: FieldSpec, value: CleanValue) -> object:
    """Valeur d'un champ du profil lue dans une cellule nettoyée (`None` = non renseignée)."""
    if value is None:
        return None
    if spec.kind is FieldKind.INTEGER:
        if not isinstance(value, Decimal) or value != value.to_integral_value():
            problem = "nombre entier attendu"
            raise CellRejected(problem)
        return int(value)
    if spec.kind is FieldKind.BOOLEAN:
        answer = _fold(str(value))
        if answer not in YES | NO:
            problem = "« Oui » ou « Non » attendu"
            raise CellRejected(problem)
        return answer in YES
    if spec.kind is FieldKind.CHOICE:
        text = str(value).strip()
        code = UNIT_LABELS.get(_fold(text), text.upper())
        if code not in spec.choices:
            problem = "valeur inconnue (« Mètre » ou « Pièce »)"
            raise CellRejected(problem)
        return code
    return value
