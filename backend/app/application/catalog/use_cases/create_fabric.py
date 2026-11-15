"""Créer un tissu avec ses couleurs, ajouter une couleur à un tissu (Textile, 2026-11-15).

`CreateFabric` : un article par couleur, « <Tissu> — <Couleur> », dans **une** transaction (une
couleur refusée → aucune créée). Tissu déjà présent → `DuplicateArticle` (409, contrainte
`article_fabric`, `existing_id` = une de ses couleurs) : l'écran propose d'ajouter une couleur.

`AddFabricColors` : nouvelles couleurs d'un tissu existant (404 s'il n'en a aucune) ; elles
reprennent tissu (graphie d'origine), prix, longueur du rouleau, « au mètre seulement » et seuil
de la première couleur (ordre du catalogue).

Droits comme `CreateArticle` : `ARTICLE_WRITE` (propriétaire, comptable) et `PRICE_SET`
(propriétaire) dès qu'un prix est fixé — y compris recopié d'une couleur existante.
"""

from dataclasses import dataclass

from app.application.catalog.fabrics import (
    Author,
    FabricTerms,
    FabricView,
    create_colors,
    fabric_articles,
    require_fabrics,
)
from app.application.catalog.use_cases.context import shop_context
from app.application.catalog.visibility import visibility_for
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of
from app.domain.catalog.errors import DuplicateArticle
from app.domain.catalog.fabric import FabricShape, clean_colors
from app.domain.catalog.prices import ArticlePrices
from app.domain.shared.errors import NotFound
from app.domain.shops.values import clean_text

FABRIC_MAX_LENGTH = 60
ARTICLE_FABRIC = "article_fabric"


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateFabricCommand:
    fabric: str
    colors: tuple[str, ...]
    terms: FabricTerms


def _fabric_name(value: str) -> str:
    return clean_text(value, "fabric", max_length=FABRIC_MAX_LENGTH)


class _FabricUseCase:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def _author(self, actor: Actor) -> Author:
        return Author(performer=performer_of(actor), user_id=actor.user_id, now=self._clock.now())

    def _require_price_right(self, actor: Actor, prices: ArticlePrices | None) -> None:
        if prices is not None and prices.set_kinds():
            self._policy.require(actor, Permission.PRICE_SET)


class CreateFabric(_FabricUseCase):
    def execute(self, actor: Actor, command: CreateFabricCommand) -> FabricView:
        self._policy.require(actor, Permission.ARTICLE_WRITE)
        self._require_price_right(actor, command.terms.prices)
        fabric, colors = _fabric_name(command.fabric), clean_colors(command.colors)
        author = self._author(actor)
        with self._uow_factory(actor_shop(actor)) as uow:
            context = shop_context(uow)
            require_fabrics(context.profile)
            existing = fabric_articles(uow, fabric)
            if existing:
                first = existing[0]
                raise DuplicateArticle(str(first.id), first.display_name, ARTICLE_FABRIC)
            created = create_colors(uow, context, fabric, colors, command.terms, author)
            uow.commit()
        return FabricView(
            fabric=fabric,
            articles=created,
            visibility=visibility_for(self._policy, actor),
            min_price_enabled=context.settings.min_price_enabled,
            shop_threshold=context.settings.low_stock_threshold,
        )


class AddFabricColors(_FabricUseCase):
    def execute(self, actor: Actor, fabric: str, colors: tuple[str, ...]) -> FabricView:
        self._policy.require(actor, Permission.ARTICLE_WRITE)
        wanted, cleaned = _fabric_name(fabric), clean_colors(colors)
        author = self._author(actor)
        with self._uow_factory(actor_shop(actor)) as uow:
            context = shop_context(uow)
            require_fabrics(context.profile)
            existing = fabric_articles(uow, wanted)
            if not existing:
                msg = "Tissu introuvable"
                raise NotFound(msg, details={"fabric": wanted})
            model = existing[0]
            fields = model.details.fields
            terms = FabricTerms(
                shape=FabricShape(
                    roll_length_m=fields.piece_length_m, meter_only=not fields.sold_by_piece
                ),
                alert_threshold=model.details.alert_threshold,
                prices=model.prices,
            )
            self._require_price_right(actor, terms.prices)
            name = fields.fabric or wanted
            created = create_colors(uow, context, name, cleaned, terms, author)
            uow.commit()
        return FabricView(
            fabric=name,
            articles=existing + created,
            visibility=visibility_for(self._policy, actor),
            min_price_enabled=context.settings.min_price_enabled,
            shop_threshold=context.settings.low_stock_threshold,
        )
