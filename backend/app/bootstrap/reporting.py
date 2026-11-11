"""Assemblage du module Tableau de bord (T19) : tableau de bord, détails, accueils par rôle.

Lecture seule : le port `DashboardQueries` est servi par les registres de persistance
(`bootstrap/persistence.py`) ; aucun handler ni alerte à brancher.
"""

from dataclasses import dataclass

from app.application.reporting.use_cases.dashboard import ReadDashboard
from app.application.reporting.use_cases.home import ReadHome
from app.application.reporting.use_cases.read_details import ReadDashboardDetail
from app.application.security.policy import Policy
from app.bootstrap.identity import IdentityModule
from app.interface.http.routes.reporting import ReportingComponents


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportingModule:
    http: ReportingComponents


def build_reporting(identity: IdentityModule) -> ReportingModule:
    uows, clock = identity.core.shop_uow_factory, identity.clock
    policy = Policy(clock=clock.now)
    dashboard = ReadDashboard(uows, policy, clock)
    http = ReportingComponents(
        dashboard=dashboard,
        details=ReadDashboardDetail(uows, policy, clock),
        home=ReadHome(uows, policy, clock, dashboard),
        guard=identity.auth.guard,
    )
    return ReportingModule(http=http)
