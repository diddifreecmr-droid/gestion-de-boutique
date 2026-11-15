"""Coûts et marges du gérant (specs § 15.1, 2026-11-15) : par article, par tissu (Textile, au
mètre et au rouleau) et jour par jour, aux coûts figés au moment de la vente.

Propriétaire seul : `DASHBOARD_READ` (comme le tableau de bord) **et** `COST_READ` (coûts et
marges, RG-D02) ; vendeur, comptable, chauffeur : 403. Mêmes périodes que le tableau de bord
(`periods.resolve_period`). Jamais servi depuis un cache (route en `no-store`).
"""

from dataclasses import dataclass
from datetime import date

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.reporting.margin_ports import MarginQueries
from app.application.reporting.margins import (
    ArticleMargin,
    DayMargin,
    FabricMargin,
    Figures,
    article_margins,
    day_margins,
    fabric_margins,
    figures_of,
)
from app.application.reporting.periods import Period, PeriodKind, resolve_period
from app.application.security.actor import Actor
from app.application.security.errors import PermissionDenied
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop


@dataclass(frozen=True, slots=True, kw_only=True)
class MarginsReport:
    period: Period
    totals: Figures
    articles: list[ArticleMargin]
    fabrics: list[FabricMargin]
    days: list[DayMargin]


class ReadMargins:
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
    ) -> MarginsReport:
        self._policy.require(actor, Permission.DASHBOARD_READ)
        if not self._policy.can_read_field(actor, Permission.COST_READ):
            raise PermissionDenied(actor, Permission.COST_READ)
        period = resolve_period(kind, self._clock.today(), first_day, last_day)
        with self._uow_factory(actor_shop(actor)) as uow:
            rows = MarginQueries.within(uow).sold_by_article(period.first_day, period.last_day)
        return MarginsReport(
            period=period,
            totals=figures_of(rows),
            articles=article_margins(rows),
            fabrics=fabric_margins(rows),
            days=day_margins(period.each_day(), rows),
        )
