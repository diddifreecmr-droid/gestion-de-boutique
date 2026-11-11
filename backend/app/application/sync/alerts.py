"""Règle d'alerte « Saisie refusée » (CDC § 20.1, specs § 6.5, recette OFF-07).

`OfflineEntryRefused` (saisie hors connexion refusée au retour du réseau, ex. vente d'un
vendeur sous le prix minimum) → propriétaires actifs, à chaque cas (pas de déduplication :
chaque saisie refusée est un fait distinct). L'auteur voit le refus sur son appareil.
« Stock à vérifier » (RG-T18) est émise par le grand livre du stock (`stock/alerts.py`).
"""

from collections.abc import Iterable

from app.application.alerts.dispatcher import AlertDirective, AlertDispatcher, AlertNotice
from app.application.ports.uow import UnitOfWork
from app.application.stock.alerts import OWNERS, recipients
from app.domain.alerts.alert import AlertType
from app.domain.sync.events import OfflineEntryRefused


def entry_refused(event: OfflineEntryRefused, uow: UnitOfWork) -> Iterable[AlertDirective]:
    return [
        AlertNotice(
            recipients=recipients(uow, OWNERS),
            type=AlertType.ENTRY_REFUSED,
            entity=event.entity,
            message=event.summary,
        )
    ]


def register_sync_alerts(dispatcher: AlertDispatcher) -> None:
    """À appeler **une fois** par répartiteur (composition root, `bootstrap/core.py`)."""
    dispatcher.register(OfflineEntryRefused, entry_refused)
