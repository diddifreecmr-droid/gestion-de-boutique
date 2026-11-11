"""UC-VEN-06 — Signaler une erreur sur une vente, et réponse du propriétaire (RPT-01, RPT-02).

- `ReportSaleError` (`SALE_ERROR_REPORT`, « Siens » pour le vendeur) : sur **l'une de ses
  ventes** seulement — la vente d'un autre vendeur → 404 (RPT-01) ; description obligatoire ;
  vente valide. L'alerte « Erreur signalée » part aux propriétaires (`sales/alerts.py`).
  Idempotent par `report_id` client.
- `AnswerErrorReport` (`SALE_UPDATE`, propriétaire) : réponse visible par le vendeur, statut
  « Traité » si demandé ; le vendeur la lit dans `GET /sales/{id}` (« le vendeur voit la
  suite donnée »).
"""

from dataclasses import dataclass

from app.application.ports.clock import Clock
from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWorkFactory
from app.application.sales.ports import ErrorReportRepository, SaleRepository
from app.application.security.access import OwnScope
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of, require_version
from app.domain.sales.error_report import ErrorReport
from app.domain.sales.ids import ErrorReportId, SaleId


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportCommand:
    sale_id: SaleId
    description: str
    report_id: ErrorReportId | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class AnswerCommand:
    report_id: ErrorReportId
    reply: str
    handled: bool = True
    version: int | None = None


class ReportSaleError:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, command: ReportCommand) -> tuple[ErrorReport, bool]:
        scope = self._policy.scope_filter(actor, Permission.SALE_ERROR_REPORT)
        own = scope.user_id if isinstance(scope, OwnScope) else None
        with self._uow_factory(actor_shop(actor)) as uow:
            sale = SaleRepository.within(uow).get(command.sale_id)
            if own is not None and sale.seller_id != own:
                raise not_found(command.sale_id)
            reports = ErrorReportRepository.within(uow)
            if command.report_id is not None:
                existing = reports.find(command.report_id)
                if existing is not None:
                    return existing, False
            sale.require_valid()
            report = ErrorReport.report(
                uow.shop_id,
                sale.id,
                str(sale.number),
                command.description,
                performer=performer_of(actor),
                now=self._clock.now(),
                report_id=command.report_id,
            )
            reports.add(report)
            uow.commit()
        return report, True


class AnswerErrorReport:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, command: AnswerCommand) -> ErrorReport:
        self._policy.require(actor, Permission.SALE_UPDATE)
        with self._uow_factory(actor_shop(actor)) as uow:
            reports = ErrorReportRepository.within(uow)
            report = reports.get(command.report_id)
            if command.version is not None:
                require_version(report.version, command.version)
            report.answer(
                command.reply,
                handled=command.handled,
                performer=performer_of(actor),
                now=self._clock.now(),
            )
            reports.update(report)
            uow.commit()
        return report
