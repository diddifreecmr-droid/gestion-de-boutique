"""Routes du Tableau de bord et des accueils (UC-TDB-01 à 05) — specs § 6.3, sous `/shops/{id}/`.

- `GET /dashboard?period=today|yesterday|week|month|last_month|custom&from=&to=` :
  propriétaire seul (`DASHBOARD_READ`) ; vendeur, comptable, chauffeur : 403.
- `GET /dashboard/details/{metric}?period=…` : liste qui explique un chiffre
  (`sales`, `payments`, `expenses`, `receivables`, `low_stock`).
- `GET /home` : accueil de son rôle (tous les membres), un seul bloc rempli.

Toutes les réponses portent `Cache-Control: no-store` : les chiffres ne sont jamais servis
depuis un cache ni affichés hors ligne (RG-T25, specs § 7.3).
"""

from dataclasses import dataclass
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.application.reporting.details import DetailMetric
from app.application.reporting.periods import PeriodKind
from app.application.reporting.use_cases.dashboard import ReadDashboard
from app.application.reporting.use_cases.home import ReadHome
from app.application.reporting.use_cases.read_details import ReadDashboardDetail
from app.application.security.actor import Actor
from app.interface.http.presenters.reporting import (
    dashboard_response,
    detail_response,
    home_response,
)
from app.interface.http.schemas.reporting import (
    DashboardDetailResponse,
    DashboardResponse,
    HomeResponse,
)
from app.interface.http.security import AuthGuard


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportingComponents:
    dashboard: ReadDashboard
    details: ReadDashboardDetail
    home: ReadHome
    guard: AuthGuard


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


def build_reporting_router(c: ReportingComponents) -> APIRouter:
    router = APIRouter(tags=["reporting"])
    Member = Annotated[Actor, Depends(c.guard.current_actor)]  # noqa: N806
    From = Annotated[date | None, Query(alias="from")]  # noqa: N806
    To = Annotated[date | None, Query(alias="to")]  # noqa: N806

    @router.get("/shops/{shop_id}/dashboard")
    def dashboard(
        actor: Member,
        response: Response,
        period: PeriodKind = PeriodKind.TODAY,
        first_day: From = None,
        last_day: To = None,
    ) -> DashboardResponse:
        _no_store(response)
        return dashboard_response(c.dashboard.execute(actor, period, first_day, last_day))

    @router.get("/shops/{shop_id}/dashboard/details/{metric}")
    def dashboard_detail(
        actor: Member,
        response: Response,
        metric: DetailMetric,
        period: PeriodKind = PeriodKind.TODAY,
        first_day: From = None,
        last_day: To = None,
    ) -> DashboardDetailResponse:
        _no_store(response)
        report = c.details.execute(actor, metric, period, first_day, last_day)
        return detail_response(report)

    @router.get("/shops/{shop_id}/home", response_model_exclude_unset=True)
    def home(actor: Member, response: Response) -> HomeResponse:
        _no_store(response)
        return home_response(c.home.execute(actor))

    return router
