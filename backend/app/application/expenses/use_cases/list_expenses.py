"""UC-DEP-03 — Consulter les dépenses (comptable, propriétaire ; recette EXP-05).

Liste **du jour** par défaut (journées de Douala, `?from=&to=`), du plus récemment saisi au
plus ancien, paginée par curseur. Filtres : période, catégorie, tag, lieu, auteur, mode de
paiement. Les dépenses annulées restent dans la liste (barrées côté écran, RG-T03) mais pas
dans les totaux : total de la période et répartition par catégorie, calculés par le port de
requête `ExpenseQuery` sur **toute** la période filtrée (pas seulement la page).

Filtre par tag : un tag fusionné désigne sa cible (les dépenses ont été réétiquetées).
"""

from dataclasses import dataclass
from datetime import date

from app.application.expenses.ports import ExpenseFilters, ExpenseQuery, ExpenseTotals
from app.application.expenses.views import ExpenseView, tag_index, view_of
from app.application.ports.clock import Clock
from app.application.ports.pagination import Cursor, PageRequest
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.domain.expenses.ids import TagId
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import UserId
from app.domain.shops.ids import ExpenseCategoryId, LocationId, PaymentModeId


@dataclass(frozen=True, slots=True, kw_only=True)
class ExpenseCriteria:
    """Filtres demandés ; période absente = aujourd'hui, `to` seul = ce jour-là."""

    first_day: date | None = None
    last_day: date | None = None
    category_id: ExpenseCategoryId | None = None
    tag_id: TagId | None = None
    location_id: LocationId | None = None
    created_by: UserId | None = None
    payment_mode_id: PaymentModeId | None = None


@dataclass(frozen=True, slots=True)
class ExpenseListing:
    items: list[ExpenseView]
    next_cursor: Cursor | None
    totals: ExpenseTotals
    first_day: date
    last_day: date


def period_of(criteria: ExpenseCriteria, today: date) -> tuple[date, date]:
    last = criteria.last_day or (
        today if criteria.first_day is None else max(criteria.first_day, today)
    )
    first = criteria.first_day or last
    if first > last:
        msg = "Période inversée : « du » est après « au »"
        raise ValidationFailed(msg, details={"field": "from"})
    return first, last


class ListExpenses:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, criteria: ExpenseCriteria, page: PageRequest) -> ExpenseListing:
        self._policy.require(actor, Permission.EXPENSE_READ)
        first, last = period_of(criteria, self._clock.today())
        now = self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            tags = tag_index(uow)
            tag_id = criteria.tag_id
            if tag_id is not None and tag_id in tags:
                tag_id = tags[tag_id].merged_into or tag_id
            filters = ExpenseFilters(
                first_day=first,
                last_day=last,
                category_id=criteria.category_id,
                tag_id=tag_id,
                location_id=criteria.location_id,
                created_by=criteria.created_by,
                payment_mode_id=criteria.payment_mode_id,
            )
            query = ExpenseQuery.within(uow)
            found = query.search(filters, page)
            totals = query.totals(filters)
        items = [view_of(actor, expense, tags, now) for expense in found.items]
        return ExpenseListing(items, found.next_cursor, totals, first, last)
