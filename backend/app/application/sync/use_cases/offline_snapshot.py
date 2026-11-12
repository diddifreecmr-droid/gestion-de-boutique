"""`GET /offline-snapshot?since=` — données gardées sur l'appareil pour saisir hors ligne (RG-T25).

Droit `offline_capture` exigé (403 `FEATURE_DISABLED` en V1, l'instantané n'est jamais
téléchargé, OFF-02). Contenu selon ce que le rôle peut **saisir** hors connexion (RG-T22) :

| Section | Qui la reçoit |
| --- | --- |
| articles actifs, prix de base et minimum (selon `CatalogVisibility`) | qui vend (`SALE_CREATE`) |
| clients (ceux du vendeur : portée OWN de `CUSTOMER_READ`, Q-20) | qui vend |
| catégories de dépenses actives | qui saisit des dépenses (`EXPENSE_CREATE`) |
| lieux actifs, modes de paiement actifs | tout rôle qui a une section ci-dessus |

**Aucun coût** (dernier coût, CMP) n'est jamais mis dans l'instantané, pour aucun rôle : la
saisie n'en a pas besoin (SEC-N01 sans exception possible). « Villes » et « voyage en cours »
(chauffeur) arrivent avec les camions au Lot 2.

`since` : **instantané complet** à chaque appel (les articles n'ont pas de date de mise à jour
au Lot 1 ; quelques centaines de lignes) ; `since` est accepté et renvoyé tel quel, `full`
vaut toujours vrai. Un différentiel pourra venir sans changer le contrat.
"""

from dataclasses import dataclass
from datetime import datetime

from app.application.catalog.ports import ArticleRepository
from app.application.catalog.search import ArticlePageRequest, ArticleQuery
from app.application.catalog.visibility import CatalogVisibility, visibility_for
from app.application.plans.entitlements import require_entitlement
from app.application.plans.ports import Entitlements
from app.application.ports.clock import Clock
from app.application.ports.pagination import MAX_LIMIT
from app.application.ports.uow import UnitOfWork, UnitOfWorkFactory
from app.application.sales.ports import CustomerQuery, CustomerRepository
from app.application.security.access import Access, OwnScope
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.security.role_matrix import access_for
from app.application.shops.context import actor_shop
from app.application.shops.ports import (
    ExpenseCategoryRepository,
    LocationRepository,
    PaymentModeRepository,
    ShopSettingsRepository,
)
from app.domain.catalog.article import Article
from app.domain.plans.entitlements import Entitlement
from app.domain.sales.customer import Customer
from app.domain.shops.expense_category import ExpenseCategory
from app.domain.shops.location import Location
from app.domain.shops.payment_mode import PaymentMode


@dataclass(frozen=True, slots=True, kw_only=True)
class OfflineSnapshot:
    generated_at: datetime
    since: datetime | None
    visibility: CatalogVisibility
    min_price_enabled: bool = False
    articles: tuple[Article, ...] = ()
    customers: tuple[Customer, ...] = ()
    expense_categories: tuple[ExpenseCategory, ...] = ()
    locations: tuple[Location, ...] = ()
    payment_modes: tuple[PaymentMode, ...] = ()


def active_articles(uow: UnitOfWork) -> tuple[Article, ...]:
    """Tous les articles actifs, page après page (ordre du catalogue)."""
    articles: list[Article] = []
    page = ArticlePageRequest(limit=MAX_LIMIT)
    while True:
        found = ArticleRepository.within(uow).search(ArticleQuery(), page)
        articles.extend(found.items)
        if found.next_cursor is None:
            return tuple(articles)
        page = ArticlePageRequest(limit=MAX_LIMIT, after=found.next_cursor)


class ReadOfflineSnapshot:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        entitlements: Entitlements,
        policy: Policy,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._entitlements = entitlements
        self._policy = policy
        self._clock = clock

    def _can(self, actor: Actor, permission: Permission) -> bool:
        return actor.role is not None and access_for(actor.role, permission) is not Access.NONE

    def execute(self, actor: Actor, since: datetime | None = None) -> OfflineSnapshot:
        shop_id = actor_shop(actor)
        self._policy.require(actor, Permission.HOME_READ)  # 404 hors boutique (specs § 8.3)
        require_entitlement(self._entitlements, shop_id, Entitlement.OFFLINE_CAPTURE)
        sells = self._can(actor, Permission.SALE_CREATE)
        spends = self._can(actor, Permission.EXPENSE_CREATE)
        snapshot = OfflineSnapshot(
            generated_at=self._clock.now(),
            since=since,
            visibility=visibility_for(self._policy, actor),
        )
        if not (sells or spends):
            return snapshot
        with self._uow_factory(shop_id) as uow:
            locations = LocationRepository.within(uow).list_all()
            modes = PaymentModeRepository.within(uow).list_all()
            settings = ShopSettingsRepository.within(uow).current().values
            categories = ExpenseCategoryRepository.within(uow).list_all() if spends else []
            articles = active_articles(uow) if sells else ()
            customers = self._customers(uow, actor) if sells else []
        return OfflineSnapshot(
            generated_at=snapshot.generated_at,
            since=since,
            visibility=snapshot.visibility,
            min_price_enabled=settings.min_price_enabled,
            articles=articles,
            customers=tuple(customers),
            expense_categories=tuple(c for c in categories if c.active),
            locations=tuple(loc for loc in locations if loc.details.active),
            payment_modes=tuple(m for m in modes if m.details.active),
        )

    def _customers(self, uow: UnitOfWork, actor: Actor) -> list[Customer]:
        scope = self._policy.scope_filter(actor, Permission.CUSTOMER_READ)
        seller = scope.user_id if isinstance(scope, OwnScope) else None
        return CustomerRepository.within(uow).search(CustomerQuery(None, seller))
