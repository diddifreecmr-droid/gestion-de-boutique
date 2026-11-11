"""Règles d'alerte des ventes, branchées sur l'`AlertDispatcher` (T09) par `bootstrap/core.py`.

- Erreur signalée (UC-VEN-06, RPT-01) : `ErrorReported` → propriétaires actifs, à chaque
  signalement (alerte « Erreur signalée » sur la vente concernée).
- Demande de prix (UC-VEN-03, E2E-06) : `PriceRequested` → propriétaires actifs (article, prix
  demandé, minimum ; l'alerte ouvre la demande, qui porte le vendeur), une seule fois par
  demande (`price_request:<id>`) ; résolue à la décision ou à l'expiration (ERR-PRM-09).
"""

from collections.abc import Iterable

from app.application.alerts.dispatcher import (
    AlertDirective,
    AlertDispatcher,
    AlertNotice,
    AlertResolution,
)
from app.application.ports.uow import UnitOfWork
from app.application.stock.alerts import OWNERS, recipients
from app.domain.alerts.alert import AlertType
from app.domain.sales.events import (
    ErrorReported,
    PriceRequestAccepted,
    PriceRequested,
    PriceRequestRefused,
)
from app.domain.sales.price_request import PriceRequestExpired


def error_reported(event: ErrorReported, uow: UnitOfWork) -> Iterable[AlertDirective]:
    return [
        AlertNotice(
            recipients=recipients(uow, OWNERS),
            type=AlertType.SALE_ERROR_REPORTED,
            entity=event.entity,
            message=event.summary[:500],
        )
    ]


def price_requested(event: PriceRequested, uow: UnitOfWork) -> Iterable[AlertDirective]:
    return [
        AlertNotice(
            recipients=recipients(uow, OWNERS),
            type=AlertType.PRICE_REQUEST,
            entity=event.entity,
            message=event.summary[:500],
            dedup_key=event.request_key,
        )
    ]


def price_request_closed(
    event: PriceRequestAccepted | PriceRequestRefused | PriceRequestExpired, uow: UnitOfWork
) -> Iterable[AlertDirective]:
    return [AlertResolution(event.request_key)]


def register_sales_alerts(dispatcher: AlertDispatcher) -> None:
    """À appeler **une fois** par répartiteur (composition root, `bootstrap/core.py`)."""
    dispatcher.register(ErrorReported, error_reported)
    dispatcher.register(PriceRequested, price_requested)
    dispatcher.register(PriceRequestAccepted, price_request_closed)
    dispatcher.register(PriceRequestRefused, price_request_closed)
    dispatcher.register(PriceRequestExpired, price_request_closed)
