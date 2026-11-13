"""Module de chaque type d'alerte (décision client specs § 15.1 « Modules par boutique »).

Une alerte d'un module éteint pour la boutique n'est pas créée (`AlertDispatcher`) : ses
points d'entrée disparaissent de l'interface, alertes comprises. Tout type d'alerte nouveau
doit déclarer son module (contrôle à l'import, fail-fast).
"""

from collections.abc import Mapping
from types import MappingProxyType

from app.domain.alerts.alert import AlertType
from app.domain.profiles.modules import Module

ALERT_MODULES: Mapping[AlertType, Module] = MappingProxyType(
    {
        AlertType.LOW_STOCK: Module.CATALOG,
        AlertType.STOCK_TO_VERIFY: Module.CATALOG,
        AlertType.STOCK_ADJUSTMENT: Module.CATALOG,
        AlertType.INVENTORY_VALIDATED: Module.CATALOG,
        AlertType.RECEIVABLE_REMINDER: Module.RECEIVABLES,
        AlertType.TRANSFER_TO_RECEIVE: Module.TRANSFERS,
        AlertType.RECEPTION_GAP: Module.TRANSFERS,
        AlertType.TRIP_EXPENSE_TO_VALIDATE: Module.TRANSPORT,
        AlertType.BREAKDOWN: Module.TRANSPORT,
        AlertType.TRUCK_SILENT: Module.TRANSPORT,
        AlertType.DOCUMENT_TO_RENEW: Module.TRANSPORT,
        AlertType.SALE_ERROR_REPORTED: Module.SALES,
        AlertType.PRICE_REQUEST: Module.SALES,
        AlertType.ENTRY_REFUSED: Module.CORE,
    }
)
if set(ALERT_MODULES) != set(AlertType):
    _msg = f"Module non déclaré pour les alertes {sorted(set(AlertType) - set(ALERT_MODULES))}"
    raise RuntimeError(_msg)


def alert_module(alert_type: AlertType) -> Module:
    return ALERT_MODULES[AlertType(alert_type)]
