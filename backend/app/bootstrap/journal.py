"""Assemblage du journal, des alertes et des droits d'offre (T09, T10).

- L'unité de travail de boutique du noyau porte les handlers `AuditRecorder` puis
  `AlertDispatcher` (même transaction que l'action, D7). Les modules métier enregistrent leurs
  règles d'alerte sur `JournalModule.alerts` (`register`).
- Les refus d'accès sont journalisés par le gestionnaire d'erreurs HTTP (`RecordAccessDenied`).
- Droits d'offre : l'offre est celle du **compte commerçant** de la boutique
  (`AccountShopPlans`, T10), surcharges de l'administrateur dans `entitlement_override`.
"""

from dataclasses import dataclass

from app.application.alerts.dispatcher import AlertDispatcher
from app.application.alerts.use_cases.my_alerts import ListAlerts, MarkAlertRead
from app.application.audit.access_denied import RecordAccessDenied
from app.application.audit.use_cases.consult import ConsultAudit
from app.application.plans.entitlements import PlanEntitlements
from app.application.plans.ports import EntitlementOverrides, Entitlements
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.policy import Policy
from app.application.shops.plans import AccountShopPlans
from app.bootstrap.config import Settings
from app.bootstrap.core import Core, build_core
from app.interface.http.routes.journal import JournalComponents
from app.interface.http.security import AuthGuard


def shop_entitlements(core: Core) -> Entitlements:
    """Droits d'offre d'une boutique : offre du compte + surcharges de l'administrateur."""
    return PlanEntitlements(AccountShopPlans(core.catalog), core.overrides)


@dataclass(frozen=True, slots=True, kw_only=True)
class JournalModule:
    uow_factory: UnitOfWorkFactory
    alerts: AlertDispatcher
    entitlements: Entitlements
    overrides: EntitlementOverrides
    http: JournalComponents


def build_journal(
    settings: Settings, *, clock: Clock, guard: AuthGuard, core: Core | None = None
) -> JournalModule:
    """`core` absent : noyau neuf (outils et tests ciblés, sans données partagées)."""
    core = core or build_core(settings, clock)
    uow_factory = core.shop_uow_factory
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
        alerts=core.alerts,
        entitlements=shop_entitlements(core),
        overrides=core.overrides,
        http=http,
    )
