"""Assemblage du journal, des alertes et des droits d'offre (T09).

- L'unité de travail de boutique reçoit les handlers `AuditRecorder` puis `AlertDispatcher`
  (même transaction que l'action, D7). Les modules métier enregistreront leurs règles
  d'alerte sur `JournalModule.alerts` (`register`).
- Les refus d'accès sont journalisés par le gestionnaire d'erreurs HTTP (`RecordAccessDenied`).
- Droits d'offre : offre gratuite pour toutes les boutiques (T10 stockera l'offre de chacune),
  surcharges de l'administrateur en mémoire ou dans `entitlement_override` selon l'adaptateur.
"""

from dataclasses import dataclass

from app.application.alerts.dispatcher import AlertDispatcher
from app.application.alerts.use_cases.my_alerts import ListAlerts, MarkAlertRead
from app.application.audit.access_denied import RecordAccessDenied
from app.application.audit.recorder import AuditRecorder
from app.application.audit.use_cases.consult import ConsultAudit
from app.application.plans.entitlements import FixedShopPlans, PlanEntitlements
from app.application.plans.ports import EntitlementOverrides, Entitlements
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.policy import Policy
from app.bootstrap.config import Settings
from app.bootstrap.persistence import build_unit_of_work_factory
from app.infrastructure.persistence.memory.entitlements import InMemoryEntitlementOverrides
from app.infrastructure.persistence.sqlalchemy.entitlements import SqlEntitlementOverrides
from app.infrastructure.persistence.sqlalchemy.uow import SqlUnitOfWorkFactory
from app.interface.http.routes.journal import JournalComponents
from app.interface.http.security import AuthGuard


@dataclass(frozen=True, slots=True, kw_only=True)
class JournalModule:
    uow_factory: UnitOfWorkFactory
    alerts: AlertDispatcher
    entitlements: Entitlements
    overrides: EntitlementOverrides
    http: JournalComponents


def build_journal(settings: Settings, *, clock: Clock, guard: AuthGuard) -> JournalModule:
    alerts = AlertDispatcher(clock)
    uow_factory = build_unit_of_work_factory(settings, [AuditRecorder(clock), alerts])
    overrides: EntitlementOverrides = (
        SqlEntitlementOverrides(uow_factory.engine)
        if isinstance(uow_factory, SqlUnitOfWorkFactory)
        else InMemoryEntitlementOverrides()
    )
    policy = Policy(clock=clock.now)
    http = JournalComponents(
        consult_audit=ConsultAudit(uow_factory, policy),
        list_alerts=ListAlerts(uow_factory, policy),
        mark_alert_read=MarkAlertRead(uow_factory, policy),
        record_access_denied=RecordAccessDenied(uow_factory, clock),
        policy=policy,
        guard=guard,
    )
    return JournalModule(
        uow_factory=uow_factory,
        alerts=alerts,
        entitlements=PlanEntitlements(FixedShopPlans(), overrides),
        overrides=overrides,
        http=http,
    )
