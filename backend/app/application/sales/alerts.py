"""Règle d'alerte des ventes, branchée sur l'`AlertDispatcher` (T09) par `bootstrap/core.py`.

- Erreur signalée (UC-VEN-06, RPT-01) : `ErrorReported` → propriétaires actifs, à chaque
  signalement (alerte « Erreur signalée » sur la vente concernée).
"""

from collections.abc import Iterable

from app.application.alerts.dispatcher import AlertDirective, AlertDispatcher, AlertNotice
from app.application.ports.uow import UnitOfWork
from app.application.stock.alerts import OWNERS, recipients
from app.domain.alerts.alert import AlertType
from app.domain.sales.events import ErrorReported


def error_reported(event: ErrorReported, uow: UnitOfWork) -> Iterable[AlertDirective]:
    return [
        AlertNotice(
            recipients=recipients(uow, OWNERS),
            type=AlertType.SALE_ERROR_REPORTED,
            entity=event.entity,
            message=event.summary[:500],
        )
    ]


def register_sales_alerts(dispatcher: AlertDispatcher) -> None:
    """À appeler **une fois** par répartiteur (composition root, `bootstrap/core.py`)."""
    dispatcher.register(ErrorReported, error_reported)
