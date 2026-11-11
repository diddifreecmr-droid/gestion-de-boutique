"""Agrégat `Article` (CDC § 20.2 ; UC-STK-01 à UC-STK-04 ; recette CAT-01 à CAT-13).

- Nom affiché calculé « Marque Modèle » (Motos) ou saisi (`ProfileFields.display_name`).
- Unicité dans la boutique : marque + modèle (profil avec « modèle »), nom affiché (profil sans
  « modèle » : prêt-à-porter, textile ; décision client specs § 15.1) et référence ; clés pliées
  (`keys.py`), contraintes `article_brand_model` / `article_name` / `article_reference`.
- Changer le nom ne réécrit rien d'autre : les ventes gardent un instantané (T16, CAT-06).
- Statut Actif / Archivé : un article archivé sort des listes de vente et d'achat mais reste
  lisible (historique, rapports). La règle « pas d'archivage avec du stock » regarde le stock :
  elle est vérifiée par le cas d'utilisation (port `ArticleStock`).
- `last_cost` et `wac` (dernier coût RG-T11, CMP RG-T12) sont **calculés par le module Achats**
  (T15) : seul `record_costs` les écrit, jamais un cas d'utilisation du catalogue.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime

from app.domain.audit.values import EntityRef, Performer
from app.domain.catalog.details import ArticleDetails, ArticleStatus, padded
from app.domain.catalog.errors import PiecePriceNotAllowed
from app.domain.catalog.events import (
    ArticleArchived,
    ArticleChanged,
    ArticleCreated,
    ArticlePricesSet,
    ArticleReactivated,
)
from app.domain.catalog.ids import ArticleId
from app.domain.catalog.prices import PIECE_KINDS, ArticlePrices, PriceChange, price_changes
from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import InvalidStateTransition
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId
from app.domain.shared.money import Money
from app.domain.shops.events import diff


@dataclass(eq=False, kw_only=True)
class Article:
    id: ArticleId
    shop_id: ShopId
    details: ArticleDetails
    created_at: datetime
    prices: ArticlePrices = field(default_factory=ArticlePrices)
    status: ArticleStatus = ArticleStatus.ACTIVE
    last_cost: Money | None = None
    wac: Money | None = None
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.created_at = require_aware(self.created_at)

    @property
    def display_name(self) -> str:
        return self.details.display_name

    @property
    def is_active(self) -> bool:
        return self.status is ArticleStatus.ACTIVE

    @property
    def entity(self) -> EntityRef:
        return EntityRef("article", self.id.value, self.display_name)

    # ------------------------------------------------------------------ création
    @classmethod
    def create(
        cls,
        shop_id: ShopId,
        details: ArticleDetails,
        *,
        performer: Performer,
        now: datetime,
        article_id: ArticleId | None = None,
    ) -> "Article":
        """Article actif, sans prix (les prix passent par `set_prices`, UC-STK-03)."""
        article = cls(
            id=article_id or ArticleId.new(), shop_id=shop_id, details=details, created_at=now
        )
        article.events.record(
            ArticleCreated(
                shop_id=shop_id,
                occurred_at=now,
                performer=performer,
                entity=article.entity,
                summary=f"Article créé : {details.display_name}",
            )
        )
        return article

    # ------------------------------------------------------------------ modification
    def change(
        self,
        details: ArticleDetails,
        *,
        performer: Performer,
        now: datetime,
        reason: str | None = None,
    ) -> bool:
        """Nouveaux détails ; avant/après au journal. `False` si rien ne change (UC-STK-02)."""
        if details.fields.sold_by_piece is False and self.prices.set_kinds() & PIECE_KINDS:
            raise PiecePriceNotAllowed("sold_by_piece")
        before, after = self.details.scalars(), details.scalars()
        keys = set(before) | set(after)
        changes = diff(padded(before, keys), padded(after, keys))
        if not changes:
            return False
        previous = self.display_name
        self.details = details
        self.events.record(
            ArticleChanged(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Article modifié : {previous}",
                changes=changes,
                reason=reason,
            )
        )
        return True

    def set_prices(
        self,
        prices: ArticlePrices,
        *,
        min_price_enabled: bool,
        performer: Performer,
        now: datetime,
    ) -> list[PriceChange]:
        """Remplace les quatre prix ; renvoie les prix changés (historique, `price_changes`)."""
        changed = price_changes(
            self.prices,
            prices,
            sold_by_piece=self.details.fields.sold_by_piece,
            min_price_enabled=min_price_enabled,
        )
        if not changed:
            return []
        changes = diff(self.prices.scalars(), prices.scalars())
        self.prices = prices
        self.events.record(
            ArticlePricesSet(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Prix modifiés : {self.display_name}",
                changes=changes,
            )
        )
        return changed

    def archive(self, *, performer: Performer, now: datetime) -> None:
        """UC-STK-04 (stock vérifié par l'appelant) ; déjà archivé → transition refusée."""
        self._move(ArticleStatus.ACTIVE, ArticleStatus.ARCHIVED, performer, now)

    def reactivate(self, *, performer: Performer, now: datetime) -> None:
        self._move(ArticleStatus.ARCHIVED, ArticleStatus.ACTIVE, performer, now)

    def record_costs(self, *, last_cost: Money | None, wac: Money | None) -> None:
        """**Réservé au module Achats (T15, Costing)** : dernier coût et CMP calculés.

        Sans événement ni journal : ces valeurs sont le résultat des achats, eux-mêmes
        journalisés. Aucun cas d'utilisation du catalogue ne doit l'appeler.
        """
        for name, value in (("last_cost", last_cost), ("wac", wac)):
            if value is not None:
                value.require_non_negative(name)
        self.last_cost, self.wac = last_cost, wac

    def _move(
        self, source: ArticleStatus, target: ArticleStatus, performer: Performer, now: datetime
    ) -> None:
        if self.status is not source:
            msg = "Article déjà archivé" if source is ArticleStatus.ACTIVE else "Article déjà actif"
            raise InvalidStateTransition(
                msg, details={"status": self.status.value, "target": target.value}
            )
        self.status = target
        event = ArticleArchived if target is ArticleStatus.ARCHIVED else ArticleReactivated
        verb = "archivé" if target is ArticleStatus.ARCHIVED else "réactivé"
        self.events.record(
            event(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Article {verb} : {self.display_name}",
                changes=diff({"status": source.value}, {"status": target.value}),
            )
        )


def with_reference(details: ArticleDetails, reference: str) -> ArticleDetails:
    """Détails avec une référence (référence générée par le cas d'utilisation)."""
    return replace(details, fields=replace(details.fields, reference=reference))
