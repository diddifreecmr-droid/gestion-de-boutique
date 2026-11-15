"""Tissu textile et ses couleurs : **un article par couleur** (décision client du 2026-11-15).

« Djampar » en rouge, bleu et vert = trois articles « Djampar — Rouge », « Djampar — Bleu »,
« Djampar — Vert », qui partagent le tissu (`fabric`), les prix au mètre et au rouleau, la
longueur du rouleau, « au mètre seulement » et le seuil. Le stock, les ventes, l'inventaire et
les marges restent ceux d'un article : aucun nouveau modèle de stock. Unité : le mètre.

- `color_article_name` : nom de l'article d'une couleur (l'unicité du nom reste celle du
  catalogue, `article_name`).
- `clean_colors` : 1 à `MAX_COLORS` couleurs, chacune avec une lettre ou un chiffre, sans
  doublon (comparées pliées : « Rouge » = « rouge ») ; sinon `ValidationFailed` sur `colors`.
- `color_fields` : champs du profil Textile d'une couleur, validés ensuite par le schéma du
  profil (`read_profile_fields`) : longueur du rouleau exigée sauf « au mètre seulement ».
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.catalog.keys import fold
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.quantity import StockUnit

SEPARATOR = " — "
MAX_COLORS = 50
COLOR_MAX_LENGTH = 40


@dataclass(frozen=True, slots=True, kw_only=True)
class FabricShape:
    """Ce que toutes les couleurs d'un tissu partagent (hors prix et seuil)."""

    roll_length_m: Decimal | None
    meter_only: bool


def color_article_name(fabric: str, color: str) -> str:
    return f"{fabric}{SEPARATOR}{color}"


def clean_colors(colors: Sequence[object]) -> tuple[str, ...]:
    if not 1 <= len(colors) <= MAX_COLORS:
        msg = f"Entre 1 et {MAX_COLORS} couleurs attendues"
        raise ValidationFailed(msg, details={"field": "colors"})
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in colors:
        color = value.strip() if isinstance(value, str) else ""
        key = fold(color)
        if not key or len(color) > COLOR_MAX_LENGTH:
            msg = f"Couleur de 1 à {COLOR_MAX_LENGTH} caractères, avec une lettre ou un chiffre"
            raise ValidationFailed(msg, details={"field": "colors", "color": str(value)})
        if key in seen:
            msg = "Couleur en double"
            raise ValidationFailed(msg, details={"field": "colors", "color": color})
        seen.add(key)
        cleaned.append(color)
    return tuple(cleaned)


def color_fields(fabric: str, color: str, shape: FabricShape) -> dict[str, object]:
    length = shape.roll_length_m
    return {
        "name": color_article_name(fabric, color),
        "fabric": fabric,
        "color": color,
        "unit": StockUnit.METER.value,
        "sold_by_piece": not shape.meter_only,
        "piece_length_m": None if length is None else str(length),
    }
