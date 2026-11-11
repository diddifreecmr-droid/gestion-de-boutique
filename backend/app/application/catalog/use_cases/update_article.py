"""UC-STK-02 — Modifier un article (propriétaire, comptable ; recette CAT-05 à CAT-07, M04).

Modification **partielle** : seuls les champs fournis changent (un champ facultatif envoyé à
`null` est effacé), avec la `version` lue (409 `VERSION_CONFLICT` sinon, ERR-VER-01). Les prix
n'y passent pas (`PUT /prices`, UC-STK-03) : un champ de prix est un champ inconnu (400).
L'ancienne et la nouvelle valeur de chaque champ vont au journal, avec le motif s'il est donné.
Changer le nom ne réécrit pas l'historique : les ventes gardent leur instantané (CAT-06).
Marque + modèle (ou référence) déjà pris par un autre article → `DuplicateArticle` (409).
"""

from collections.abc import Mapping
from typing import Any

from app.application.catalog.ports import ArticleRepository
from app.application.catalog.use_cases.context import (
    COMMON_FIELDS,
    ArticleInput,
    build_details,
    ensure_reference,
    require_unique,
    shop_context,
)
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of, require_version
from app.domain.catalog.article import Article
from app.domain.catalog.details import ArticleDetails
from app.domain.catalog.ids import ArticleId
from app.domain.profiles.profile import ShopProfile
from app.domain.shops.values import clean_optional

REASON_MAX_LENGTH = 500


class UpdateArticle:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(
        self,
        actor: Actor,
        article_id: ArticleId,
        patch: Mapping[str, Any],
        version: int,
        reason: str | None = None,
    ) -> Article:
        """`patch` : codes des champs du profil et/ou `alert_threshold`, `photo_id`, `notes`."""
        self._policy.require(actor, Permission.ARTICLE_WRITE)
        motive = clean_optional(reason, "reason", max_length=REASON_MAX_LENGTH)
        with self._uow_factory(actor_shop(actor)) as uow:
            articles = ArticleRepository.within(uow)
            article = articles.get(article_id)
            require_version(article.version, version)
            profile = shop_context(uow).profile
            details = build_details(profile, _merged(article.details, profile, patch))
            require_unique(articles, details, own_id=article.id)
            details = ensure_reference(uow, profile, details)
            changed = article.change(
                details, performer=performer_of(actor), now=self._clock.now(), reason=motive
            )
            if changed:
                articles.update(article)
                uow.commit()
        return article


def _merged(
    current: ArticleDetails, profile: ShopProfile, patch: Mapping[str, Any]
) -> ArticleInput:
    fields = current.profile_values(profile)
    fields.update({k: v for k, v in patch.items() if k not in COMMON_FIELDS})
    common: dict[str, Any] = {
        "alert_threshold": current.alert_threshold,
        "photo_id": current.photo_id,
        "notes": current.notes,
    }
    common.update({k: v for k, v in patch.items() if k in COMMON_FIELDS})
    return ArticleInput(fields=fields, **common)
