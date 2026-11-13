"""UC-TDB-05 — Accueil de son rôle (`HOME_READ` : tous, chacun le sien ; CDC § 14).

- **Propriétaire** : le tableau de bord du jour (UC-TDB-01), qui est son accueil.
- **Vendeur** : **mes** ventes du jour (nombre et montant, mêmes règles que le § 14.1 sur la
  portée « Siens »), **mes** rappels de créance du jour, saisies en attente d'envoi (toujours
  0 : saisie hors ligne désactivée, TR-26). Jamais de marge ni de coût (RG-D02).
- **Comptable** : déplacements à réceptionner (Lot 2 : non disponible), alertes de stock bas,
  valeur du stock, dépenses du jour. Aucune vente ni chiffre d'affaires (RG-D03).
- **Chauffeur** : voyage en cours et ses dépenses relèvent du Lot 2 : accueil vide
  **documenté** (chaque bloc « non disponible »).

Modules éteints (specs § 15.1) : sans `receivables`, `reminders_due` du vendeur vaut `None` ;
sans `expenses`, `expenses` du comptable vaut `None` ; sans `transfers`, ses déplacements à
réceptionner valent `None` ; sans `transport`, les blocs du chauffeur valent `None`.

Chaque bloc revérifie la permission métier qu'il lit (`SALE_READ`, `STOCK_VALUE_READ`,
`EXPENSE_READ`) : la matrice reste le seul juge, l'accueil ne l'élargit jamais. L'administrateur
plateforme avec délégation (lecture seule) voit l'accueil du propriétaire.
"""

from dataclasses import dataclass
from datetime import date

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.reporting.indicators import expenses_only, total_of
from app.application.reporting.periods import Period, PeriodKind
from app.application.reporting.ports import DashboardQueries
from app.application.reporting.reading import figures_by_day
from app.application.reporting.stock_figures import stock_figures
from app.application.reporting.use_cases.dashboard import DashboardReport, ReadDashboard
from app.application.reporting.views import LOT_2, NotAvailable
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.application.shops.modules import enabled_modules, module_enabled
from app.application.stock.use_cases.stock_value import Valuation
from app.domain.profiles.modules import Module
from app.domain.shared.roles import Role

PENDING_UPLOADS_OFFLINE_DISABLED = 0
"""Saisies en attente d'envoi : toujours 0 au Lot 1 (saisie hors ligne désactivée, TR-26)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class SellerHome:
    sales_count: int
    sales_amount: int
    reminders_due: int | None
    pending_uploads: int = PENDING_UPLOADS_OFFLINE_DISABLED


@dataclass(frozen=True, slots=True, kw_only=True)
class AccountantHome:
    low_stock: int
    stock_value: Valuation
    expenses: int | None
    transfers_to_receive: NotAvailable | None = LOT_2


@dataclass(frozen=True, slots=True, kw_only=True)
class DriverHome:
    current_trip: NotAvailable | None = LOT_2
    trip_expenses: NotAvailable | None = LOT_2


@dataclass(frozen=True, slots=True, kw_only=True)
class Home:
    role: Role
    today: date
    owner: DashboardReport | None = None
    seller: SellerHome | None = None
    accountant: AccountantHome | None = None
    driver: DriverHome | None = None


class ReadHome:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        policy: Policy,
        clock: Clock,
        dashboard: ReadDashboard,
    ) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock
        self._dashboard = dashboard

    def execute(self, actor: Actor) -> Home:
        self._policy.require(actor, Permission.HOME_READ)
        today = self._clock.today()
        role = Role.OWNER if actor.is_platform_admin else actor.role
        if role is Role.OWNER:
            return Home(role=role, today=today, owner=self._dashboard.execute(actor))
        if role is Role.SELLER:
            return Home(role=role, today=today, seller=self._seller(actor, today))
        if role is Role.ACCOUNTANT:
            return Home(role=role, today=today, accountant=self._accountant(actor, today))
        if role is Role.DRIVER:
            return Home(role=role, today=today, driver=self._driver(actor))
        msg = f"Accueil non défini pour le rôle {role!r}"
        raise RuntimeError(msg)

    def _seller(self, actor: Actor, today: date) -> SellerHome:
        self._policy.require(actor, Permission.SALE_READ)
        day = Period(PeriodKind.TODAY, today, today)
        with self._uow_factory(actor_shop(actor)) as uow:
            mine = total_of(figures_by_day(uow, day, seller=actor.user_id))
            reminders = None
            if module_enabled(uow, Module.RECEIVABLES):
                queries = DashboardQueries.within(uow)
                reminders = queries.reminders_due(today, responsible=actor.user_id)
        return SellerHome(
            sales_count=mine.sales_count, sales_amount=mine.sales, reminders_due=reminders
        )

    def _accountant(self, actor: Actor, today: date) -> AccountantHome:
        self._policy.require(actor, Permission.STOCK_VALUE_READ)
        self._policy.require(actor, Permission.EXPENSE_READ)
        with self._uow_factory(actor_shop(actor)) as uow:
            modules = enabled_modules(uow)
            expenses = None
            if Module.EXPENSES in modules:
                flows = DashboardQueries.within(uow).expense_flows(today, today)
                expenses = expenses_only([today], flows).expenses
            stock = stock_figures(uow)
        return AccountantHome(
            low_stock=stock.low_stock,
            stock_value=stock.sellable,
            expenses=expenses,
            transfers_to_receive=LOT_2 if Module.TRANSFERS in modules else None,
        )

    def _driver(self, actor: Actor) -> DriverHome:
        with self._uow_factory(actor_shop(actor)) as uow:
            transport = module_enabled(uow, Module.TRANSPORT)
        return DriverHome() if transport else DriverHome(current_trip=None, trip_expenses=None)
