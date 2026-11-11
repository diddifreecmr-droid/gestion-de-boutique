"""Port de la synchronisation : opérations reçues, clé primaire = `op_id` (idempotence, TR-11).

Pas de contrainte d'unicité métier : l'identifiant client suffit (deux envois concurrents du
même `op_id` : le second échoue au `commit` par `Duplicate`, et relit le résultat du premier).
"""

from app.application.shops.ports import ShopRecordRepository
from app.domain.sync.operation import SyncOperation, SyncOperationId


class SyncOperationRepository(ShopRecordRepository[SyncOperationId, SyncOperation]):
    """Opérations hors connexion déjà traitées dans la boutique."""
