"""Assemblage de l'ossature hors connexion (T23) : `POST /sync` et instantané hors ligne.

- Exécution par **les** cas d'utilisation en ligne : `RecordSale` du module Ventes (même grand
  livre, mode différé) et `RecordExpense` du module Dépenses — aucune règle dupliquée.
- Droits d'offre : ceux du journal (`JournalModule.entitlements` : offre du compte +
  surcharges de l'administrateur). En V1, faux partout → 403 `FEATURE_DISABLED`.
- La règle d'alerte « Saisie refusée » est branchée par le noyau (`bootstrap/core.py`).
"""

from dataclasses import dataclass

from app.application.security.policy import Policy
from app.application.sync.runner import OperationRunner
from app.application.sync.use_cases.offline_snapshot import ReadOfflineSnapshot
from app.application.sync.use_cases.sync_operations import SyncOperations
from app.bootstrap.expenses import ExpensesModule
from app.bootstrap.identity import IdentityModule
from app.bootstrap.journal import JournalModule
from app.bootstrap.sales import SalesModule
from app.interface.http.routes.sync_components import SyncComponents


@dataclass(frozen=True, slots=True, kw_only=True)
class SyncModule:
    http: SyncComponents


def build_sync(
    identity: IdentityModule,
    journal: JournalModule,
    sales: SalesModule,
    expenses: ExpensesModule,
) -> SyncModule:
    clock, uows = identity.clock, identity.core.shop_uow_factory
    runner = OperationRunner(sales.http.record, expenses.http.record)
    http = SyncComponents(
        sync=SyncOperations(uows, journal.entitlements, runner, clock, Policy(clock=clock.now)),
        snapshot=ReadOfflineSnapshot(uows, journal.entitlements, Policy(clock=clock.now), clock),
        guard=identity.auth.guard,
    )
    return SyncModule(http=http)
