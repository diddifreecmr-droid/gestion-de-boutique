"""UC-ACH-05 — Consulter les achats (comptable, propriétaire ; recette PUR-11) et lire un achat.

Liste par **date d'achat décroissante** (`position`), paginée par curseur. Filtres : période
(journées de Douala, sur la date d'achat ; défaut : du 1er du mois à aujourd'hui), fournisseur,
article, lieu. Totaux de **toute** la période filtrée en tête (nombre, marchandise, frais,
total, payé), annulés exclus (RG-T03) mais visibles dans la liste.
"""

from dataclasses import dataclass
from datetime import date

from app.application.ports.clock import Clock
from app.application.ports.pagination import Cursor, PageRequest, paginate
from app.application.ports.uow import UnitOfWorkFactory
from app.application.purchasing.ports import PurchaseRepository, position
from app.application.purchasing.views import PurchaseView, view_of
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.domain.catalog.ids import ArticleId
from app.domain.purchasing.ids import PurchaseId, SupplierId
from app.domain.purchasing.purchase import Purchase
from app.domain.purchasing.rules import PurchaseStatus
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.money import Money
from app.domain.shops.ids import LocationId


@dataclass(frozen=True, slots=True, kw_only=True)
class PurchaseCriteria:
    first_day: date | None = None
    last_day: date | None = None
    supplier_id: SupplierId | None = None
    article_id: ArticleId | None = None
    location_id: LocationId | None = None

    def matches(self, purchase: Purchase) -> bool:
        details = purchase.details
        return (
            (self.supplier_id is None or details.supplier_id == self.supplier_id)
            and (self.location_id is None or details.location_id == self.location_id)
            and (
                self.article_id is None
                or any(line.article_id == self.article_id for line in details.lines)
            )
        )


@dataclass(frozen=True, slots=True)
class PurchaseTotals:
    count: int
    merchandise: Money
    fees: Money
    total: Money
    paid: Money


@dataclass(frozen=True, slots=True)
class PurchaseListing:
    items: list[PurchaseView]
    next_cursor: Cursor | None
    totals: PurchaseTotals
    first_day: date
    last_day: date


def period_of(first: date | None, last: date | None, today: date) -> tuple[date, date]:
    last_day = last or max(today, first or today)
    first_day = first or last_day.replace(day=1)
    if first_day > last_day:
        msg = "Période inversée : « du » est après « au »"
        raise ValidationFailed(msg, details={"field": "from"})
    return first_day, last_day


def totals_of(purchases: list[Purchase]) -> PurchaseTotals:
    valid = [p for p in purchases if p.status is PurchaseStatus.VALID]
    return PurchaseTotals(
        count=len(valid),
        merchandise=Money.total(p.merchandise_total for p in valid),
        fees=Money.total(p.fees_total for p in valid),
        total=Money.total(p.total for p in valid),
        paid=Money.total(p.paid for p in valid),
    )


def find_purchases(
    repository: PurchaseRepository, criteria: PurchaseCriteria, first: date, last: date
) -> list[Purchase]:
    return [p for p in repository.list_between(first, last) if criteria.matches(p)]


class ListPurchases:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(
        self, actor: Actor, criteria: PurchaseCriteria, page: PageRequest
    ) -> PurchaseListing:
        self._policy.require(actor, Permission.PURCHASE_READ)
        today = self._clock.today()
        first, last = period_of(criteria.first_day, criteria.last_day, today)
        with self._uow_factory(actor_shop(actor)) as uow:
            found = find_purchases(PurchaseRepository.within(uow), criteria, first, last)
        served = paginate(found, page, position)
        items = [view_of(actor, purchase, today) for purchase in served.items]
        return PurchaseListing(items, served.next_cursor, totals_of(found), first, last)


class GetPurchase:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, purchase_id: PurchaseId) -> PurchaseView:
        self._policy.require(actor, Permission.PURCHASE_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            purchase = PurchaseRepository.within(uow).get(purchase_id)
        return view_of(actor, purchase, self._clock.today())
