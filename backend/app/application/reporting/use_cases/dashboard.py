"""UC-TDB-01, 02, 03 — Tableau de bord du propriétaire (`DASHBOARD_READ`, RG-D02, RG-D03).

De haut en bas (CDC § 14) : ventes, argent encaissé et marge (dernier coût et CMP, écart) avec la
comparaison à la période précédente ; dépenses et résultat simple ; créances (total à recevoir,
versements reçus, rappels du jour) ; stock (valeur, alertes de stock bas, stock à vérifier,
déplacements en route : Lot 2) ; camions (Lot 2) ; alertes en attente (erreurs signalées,
demandes de prix). Indicateurs définis dans `indicators.py` seulement.

- Période (UC-TDB-02) : `periods.resolve_period`, journées de Douala ; plusieurs jours → série
  jour par jour, total et moyenne par jour.
- Une seule lecture des sommes couvre la période **et** la précédente (comparaison).
- Les états (créances, stock, alertes) sont ceux de **maintenant**, quelle que soit la période.
- Jamais servi hors ligne (RG-T25) : l'API ne met rien en cache (`no-store`, § 7.3).
- Modules éteints (specs § 15.1) : sans `expenses`, `summary.expenses` vaut `None` et aucune
  dépense n'est lue (résultat simple = marge) ; sans `receivables`, le bloc `receivables` vaut
  `None` ; sans `transfers`, `transfers_in_transit` vaut `None` ; sans `transport`, `trucks` et
  `transport_expenses` valent `None`. L'argent encaissé reste l'argent réellement reçu.
"""

from dataclasses import dataclass, replace
from datetime import date

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.reporting.indicators import total_of
from app.application.reporting.periods import Period, PeriodKind, resolve_period
from app.application.reporting.ports import DashboardQueries, PendingAlerts
from app.application.reporting.reading import figures_by_day
from app.application.reporting.stock_figures import StockFigures, stock_figures
from app.application.reporting.views import (
    LOT_2,
    Compared,
    NotAvailable,
    Series,
    Summary,
    series_of,
    summary_of,
)
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop
from app.application.shops.modules import enabled_modules
from app.domain.profiles.modules import Module


@dataclass(frozen=True, slots=True, kw_only=True)
class ReceivablesBlock:
    total_due: int
    debtor_count: int
    received: Compared
    """Versements reçus sur la période (acomptes exclus, Q-24)."""
    reminders_due: int


@dataclass(frozen=True, slots=True, kw_only=True)
class DashboardReport:
    period: Period
    previous: Period
    summary: Summary
    series: Series | None
    receivables: ReceivablesBlock | None
    stock: StockFigures
    alerts: PendingAlerts
    transfers_in_transit: NotAvailable | None = LOT_2
    trucks: NotAvailable | None = LOT_2
    transport_expenses: NotAvailable | None = LOT_2


class ReadDashboard:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(
        self,
        actor: Actor,
        kind: PeriodKind = PeriodKind.TODAY,
        first_day: date | None = None,
        last_day: date | None = None,
    ) -> DashboardReport:
        self._policy.require(actor, Permission.DASHBOARD_READ)
        now = self._clock.now()
        today = self._clock.today()
        period = resolve_period(kind, today, first_day, last_day)
        previous = period.previous()
        both = Period(period.kind, previous.first_day, period.last_day)
        with self._uow_factory(actor_shop(actor)) as uow:
            modules = enabled_modules(uow)
            days = figures_by_day(uow, both, expenses=Module.EXPENSES in modules)
            queries = DashboardQueries.within(uow)
            position, reminders = None, 0
            if Module.RECEIVABLES in modules:
                position = queries.receivables_position()
                reminders = queries.reminders_due(today)
            alerts = queries.pending_alerts(now)
            stock = stock_figures(uow)
        current = [d for d in days if d.day >= period.first_day]
        before = total_of(d for d in days if d.day < period.first_day)
        figures = total_of(current)
        summary = summary_of(figures, before)
        transport = LOT_2 if Module.TRANSPORT in modules else None
        return DashboardReport(
            period=period,
            previous=previous,
            summary=summary if Module.EXPENSES in modules else replace(summary, expenses=None),
            series=series_of(current),
            receivables=None
            if position is None
            else ReceivablesBlock(
                total_due=position.total_due,
                debtor_count=position.debtor_count,
                received=Compared(figures.installments, before.installments),
                reminders_due=reminders,
            ),
            stock=stock,
            alerts=alerts,
            transfers_in_transit=LOT_2 if Module.TRANSFERS in modules else None,
            trucks=transport,
            transport_expenses=transport,
        )
