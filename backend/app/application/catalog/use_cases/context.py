"""Aides communes aux cas d'utilisation du catalogue : profil, unicité proposée, référence.

- `ArticleInput` : ce que l'utilisateur saisit (champs du profil + seuil, photo, notes) ; le
  domaine le valide contre le schéma du profil de la boutique (`read_profile_fields`).
- `require_unique` : un article de même marque + modèle, de même nom (profil sans modèle) ou de
  même référence existe déjà →
  `DuplicateArticle` avec `existing_id` : l'écran le **propose** au lieu d'en créer un second
  (UC-STK-01). Une course entre deux créations simultanées reste arbitrée par la contrainte du
  dépôt (`Duplicate`, 409, sans `existing_id`).
- `ensure_reference` : référence **générée si vide** pour les profils qui en ont une (CDC
  § 18.2, § 19.2). Format `REF-000001` : compteur continu par boutique (numérotation sans trou,
  type `DocType.ARTICLE`) ; un numéro déjà pris à la main est sauté.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.application.catalog.ports import (
    ARTICLE_BRAND_MODEL,
    ARTICLE_NAME,
    ARTICLE_REFERENCE,
    ArticleRepository,
    PriceHistoryLog,
)
from app.application.ports.uow import UnitOfWork
from app.application.shops.ports import ShopRepository, ShopSettingsRepository
from app.domain.catalog.article import Article, with_reference
from app.domain.catalog.details import ArticleDetails
from app.domain.catalog.errors import DuplicateArticle
from app.domain.catalog.ids import ArticleId, AttachmentId
from app.domain.catalog.prices import PriceChange, PriceHistory
from app.domain.catalog.schema import read_profile_fields
from app.domain.profiles.profile import ShopProfile
from app.domain.profiles.registry import profile_for
from app.domain.shared.doc_number import DocType
from app.domain.shared.ids import UserId
from app.domain.shops.settings import SettingsValues

MAX_REFERENCE_ATTEMPTS = 1000
COMMON_FIELDS = frozenset({"alert_threshold", "photo_id", "notes"})


@dataclass(frozen=True, slots=True, kw_only=True)
class ArticleInput:
    fields: Mapping[str, object] = field(default_factory=dict)
    """Champs du profil, par code (`ShopProfile.article_fields`)."""
    alert_threshold: Decimal | None = None
    photo_id: AttachmentId | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class ShopCatalogContext:
    profile: ShopProfile
    settings: SettingsValues


def shop_context(uow: UnitOfWork) -> ShopCatalogContext:
    shop = ShopRepository.within(uow).current()
    settings = ShopSettingsRepository.within(uow).current()
    return ShopCatalogContext(profile_for(shop.profile_code), settings.values)


def build_details(profile: ShopProfile, data: ArticleInput) -> ArticleDetails:
    return ArticleDetails(
        fields=read_profile_fields(profile, data.fields),
        alert_threshold=data.alert_threshold,
        photo_id=data.photo_id,
        notes=data.notes,
    )


def require_unique(
    articles: ArticleRepository, details: ArticleDetails, own_id: ArticleId | None = None
) -> None:
    for constraint, key in (
        (ARTICLE_BRAND_MODEL, details.brand_model_key),
        (ARTICLE_NAME, details.name_key),
        (ARTICLE_REFERENCE, details.reference_key),
    ):
        if key is None:
            continue
        existing = articles.find_by_key(constraint, key)
        if existing is not None and existing.id != own_id:
            raise DuplicateArticle(str(existing.id), existing.display_name, constraint)


def ensure_reference(
    uow: UnitOfWork, profile: ShopProfile, details: ArticleDetails
) -> ArticleDetails:
    """Détails avec une référence : celle saisie, ou la suivante libre `REF-…`."""
    has_reference = any(spec.code == "reference" for spec in profile.article_fields)
    if not has_reference or details.fields.reference is not None:
        return details
    articles = ArticleRepository.within(uow)
    for _ in range(MAX_REFERENCE_ATTEMPTS):
        candidate = with_reference(details, str(uow.numbering.next(DocType.ARTICLE)))
        key = candidate.reference_key
        if key is not None and articles.find_by_key(ARTICLE_REFERENCE, key) is None:
            return candidate
    msg = f"Aucune référence libre après {MAX_REFERENCE_ATTEMPTS} essais"
    raise RuntimeError(msg)


def find_existing(uow: UnitOfWork, article_id: ArticleId | None) -> Article | None:
    """Rejeu idempotent d'une création (`id` client déjà connu dans la boutique)."""
    return None if article_id is None else ArticleRepository.within(uow).find(article_id)


def record_history(
    uow: UnitOfWork,
    article: Article,
    changes: list[PriceChange],
    *,
    author_id: UserId,
    at: datetime,
) -> None:
    """Une ligne d'historique par prix changé (UC-STK-03 : date, ancien, nouveau, auteur)."""
    history = PriceHistoryLog.within(uow)
    for change in changes:
        history.append(
            PriceHistory.record(uow.shop_id, article.id, change, author_id=author_id, at=at)
        )
