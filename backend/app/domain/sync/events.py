"""Événement de la synchronisation hors connexion (specs § 6.5, CDC § 20.1 « Saisie refusée »).

`OfflineEntryRefused` : une saisie faite hors connexion, rejouée par `POST /sync`, a été refusée
par le serveur (ex. vente d'un vendeur sous le prix minimum, UC-VEN-03). Journalisée (action
« Rejeter », module `sync`) et convertie en alerte « Saisie refusée » aux propriétaires.
"""

from dataclasses import dataclass

from app.domain.audit.values import AuditAction
from app.domain.shared.ids import UserId
from app.domain.shops.events import ShopAuditedEvent

SYNC_MODULE = "sync"


@dataclass(frozen=True, kw_only=True)
class OfflineEntryRefused(ShopAuditedEvent):
    author_id: UserId
    op_type: str
    error_code: str
    provisional_number: str | None = None

    action = AuditAction.REJECT
    module = SYNC_MODULE
    sensitive = True
