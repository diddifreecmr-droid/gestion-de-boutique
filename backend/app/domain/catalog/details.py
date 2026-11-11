"""Détails d'un article : champs du profil + champs communs (seuil, photo, notes) — UC-STK-01.

- Seuil d'alerte : facultatif ; absent, le **réglage de la boutique** s'applique
  (`effective_threshold`, recette LOW-02). Quantité ≥ 0 dans l'unité de stock (entière pour
  l'unité ou la pièce, au dixième pour le mètre, RG-T08).
- Photo : identifiant de pièce jointe facultatif (la pièce jointe elle-même viendra avec TR-17).
- `scalars()` aplatit les détails pour le journal (avant/après champ par champ, UC-STK-02).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.audit.values import Scalar
from app.domain.catalog.ids import AttachmentId
from app.domain.catalog.keys import identity_key, search_key, sort_key
from app.domain.catalog.schema import ProfileFields
from app.domain.profiles.profile import ShopProfile
from app.domain.shared.quantity import Quantity
from app.domain.shops.values import clean_optional

NOTES_MAX_LENGTH = 500


class ArticleStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True, kw_only=True)
class ArticleDetails:
    fields: ProfileFields
    alert_threshold: Decimal | None = None
    photo_id: AttachmentId | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.fields, ProfileFields):
            msg = "ArticleDetails.fields doit être un ProfileFields"
            raise TypeError(msg)
        if self.alert_threshold is not None:
            threshold = Quantity.of(self.alert_threshold, self.fields.stock_unit)
            threshold.require_non_negative("alert_threshold")
            object.__setattr__(self, "alert_threshold", threshold.value)
        if self.photo_id is not None and not isinstance(self.photo_id, AttachmentId):
            msg = "ArticleDetails.photo_id doit être un AttachmentId"
            raise TypeError(msg)
        notes = clean_optional(self.notes, "notes", max_length=NOTES_MAX_LENGTH)
        object.__setattr__(self, "notes", notes)

    # ------------------------------------------------------------------ clés
    @property
    def display_name(self) -> str:
        return self.fields.display_name

    @property
    def brand_model_key(self) -> str | None:
        """Unicité marque + modèle : seulement pour un profil qui a un champ « modèle »."""
        brand, model = self.fields.brand, self.fields.model
        return None if brand is None or model is None else identity_key(brand, model)

    @property
    def name_key(self) -> str | None:
        """Unicité du nom affiché (prêt-à-porter, textile) : profils **sans** « modèle »."""
        if self.fields.model is not None:
            return None
        return identity_key(self.fields.display_name)

    @property
    def reference_key(self) -> str | None:
        reference = self.fields.reference
        return None if reference is None else identity_key(reference)

    @property
    def search_key(self) -> str:
        f = self.fields
        return search_key((f.display_name, f.brand, f.model, f.reference))

    @property
    def sort_key(self) -> str:
        return sort_key(self.fields.display_name)

    def effective_threshold(self, shop_default: Decimal) -> Decimal:
        """Seuil d'alerte appliqué : celui de l'article, sinon celui de la boutique."""
        return shop_default if self.alert_threshold is None else self.alert_threshold

    # ------------------------------------------------------------------ lectures
    def profile_values(self, profile: ShopProfile) -> dict[str, object]:
        """Valeurs saisies des champs du profil (point de départ d'une modification partielle)."""
        f = self.fields
        promoted: dict[str, object] = {
            "name": f.display_name,
            "brand": f.brand,
            "model": f.model,
            "reference": f.reference,
            "unit": f.stock_unit.value,
            "sold_by_piece": f.sold_by_piece,
            "piece_length_m": None if f.piece_length_m is None else str(f.piece_length_m),
        }
        values: dict[str, object] = {}
        for spec in profile.article_fields:
            values[spec.code] = promoted.get(spec.code, f.attributes.get(spec.code))
        return values

    def scalars(self) -> dict[str, Scalar]:
        f = self.fields
        values: dict[str, Scalar] = {
            "display_name": f.display_name,
            "brand": f.brand,
            "model": f.model,
            "reference": f.reference,
            "stock_unit": f.stock_unit.value,
            "sold_by_piece": f.sold_by_piece,
            "piece_length_m": None if f.piece_length_m is None else str(f.piece_length_m),
            "alert_threshold": None if self.alert_threshold is None else str(self.alert_threshold),
            "photo_id": None if self.photo_id is None else str(self.photo_id),
            "notes": self.notes,
        }
        return values | dict(f.attributes)


def padded(values: Mapping[str, Scalar], keys: set[str]) -> dict[str, Scalar]:
    """Complète par `None` les attributs absents (comparaison avant/après sur les mêmes clés)."""
    return {key: values.get(key) for key in sorted(keys)}
