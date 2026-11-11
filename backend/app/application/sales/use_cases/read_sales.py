"""UC-VEN-05 — Consulter les ventes (SAL-09 à SAL-11) et lire une vente.

- Portée « Siens » du vendeur appliquée **dans la requête** du dépôt (`seller`) : il ne voit
  que ses ventes et ses totaux (SAL-10) ; la vente d'un autre → 404 (pas de fuite).
- Liste **du jour** par défaut, plus récente en haut ; filtres période (journées de Douala),
  vendeur, article, mode de paiement, comptant / crédit. Annulées visibles (pastille).
- Recherche `q` (RG-M02, RG-T06) : numéro définitif ou provisoire, ou numéro de châssis
  (normalisé) ; **sans période donnée, elle porte sur toutes les dates**.
- **Totaux (Q-09)** : ventes datées de la période moins ventes **annulées pendant** la période
  (une annulation compte le jour où elle est faite ; une journée passée ne change jamais).
"""

from dataclasses import dataclass
from datetime import date

from app.application.ports.clock import Clock
from app.application.ports.pagination import Cursor, PageRequest, paginate
from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWorkFactory
from app.application.sales.ports import ErrorReportRepository, SaleRepository, position
from app.application.sales.search import SaleCriteria, reference_terms
from app.application.sales.views import SaleView, view_of
from app.application.security.access import OwnScope
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.domain.sales.ids import SaleId
from app.domain.sales.sale import Sale
from app.domain.sales.values import SaleStatus
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import UserId
from app.domain.shared.money import Money


@dataclass(frozen=True, slots=True)
class SaleTotals:
    count: int
    total: Money
    paid: Money


@dataclass(frozen=True, slots=True)
class SaleListing:
    items: list[SaleView]
    next_cursor: Cursor | None
    totals: SaleTotals
    first_day: date | None
    last_day: date | None


def seller_scope(policy: Policy, actor: Actor, wanted: UserId | None = None) -> UserId | None:
    """Vendeur dont la requête lit les ventes : soi-même en portée OWN, sinon le filtre."""
    scope = policy.scope_filter(actor, Permission.SALE_READ)
    return scope.user_id if isinstance(scope, OwnScope) else wanted


def totals_of(sold: list[Sale], cancelled: list[Sale]) -> SaleTotals:
    return SaleTotals(
        count=len(sold) - len(cancelled),
        total=Money.total(s.total for s in sold) - Money.total(s.total for s in cancelled),
        paid=Money.total(s.paid for s in sold) - Money.total(s.paid for s in cancelled),
    )


class ListSales:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, criteria: SaleCriteria, page: PageRequest) -> SaleListing:
        seller = seller_scope(self._policy, actor, criteria.seller_id)
        today = self._clock.today()
        dated = criteria.first_day is not None or criteria.last_day is not None
        first = criteria.first_day or criteria.last_day or today
        last = criteria.last_day or max(today, first)
        if first > last:
            msg = "Période inversée : « du » est après « au »"
            raise ValidationFailed(msg, details={"field": "from"})
        with self._uow_factory(actor_shop(actor)) as uow:
            sales = SaleRepository.within(uow)
            if criteria.text is not None:
                number, chassis = reference_terms(criteria.text)
                found = sales.find_by_reference(number, chassis, seller=seller)
                if dated:
                    found = [s for s in found if first <= s.content.sold_on <= last]
                cancelled = [s for s in found if s.status is SaleStatus.CANCELLED]
            else:
                found = sales.list_between(first, last, seller=seller)
                cancelled = sales.cancelled_between(first, last, seller=seller)
        found = [s for s in found if criteria.matches(s)]
        cancelled = [s for s in cancelled if criteria.matches(s)]
        served = paginate(found, page, position)
        items = [view_of(self._policy, actor, sale) for sale in served.items]
        searched = criteria.text is not None and not dated
        return SaleListing(
            items,
            served.next_cursor,
            totals_of(found, cancelled),
            None if searched else first,
            None if searched else last,
        )


class GetSale:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy) -> None:
        self._uow_factory = uow_factory
        self._policy = policy

    def execute(self, actor: Actor, sale_id: SaleId) -> SaleView:
        seller = seller_scope(self._policy, actor)
        with self._uow_factory(actor_shop(actor)) as uow:
            sale = SaleRepository.within(uow).get(sale_id)
            if seller is not None and sale.seller_id != seller:
                raise not_found(sale_id)
            reports = tuple(ErrorReportRepository.within(uow).for_sale(sale.id))
        return view_of(self._policy, actor, sale, reports=reports)
