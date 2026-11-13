"""`POST /imports/{id}/cancel` — annuler un lot (UC-IMP-03, décision client QC-6, T35).

Ordre : propriétaire seul (`IMPORT_CANCEL`, 403) → lot de la boutique (404) → lot encore
importé (422 `INVALID_STATE_TRANSITION`) et dans les 7 jours calendaires inclus (422
`IMPORT_CANCEL_TOO_LATE`, `ImportBatch.cancel`) → aucune opération ne touche le lot (422
`IMPORT_CANCEL_BLOCKED`, `details.blocking` : `[{type, number}]`) → retrait de ce que le lot a
créé (`withdraw_items` : rien n'est effacé, noms et téléphones libérés) → lot « Annulé ».

**Une seule transaction** : refus = rien ne change. Journal : « Annuler » sur le lot
(sensible) et l'événement de chaque élément retiré, dans la même transaction. Deux annulations
simultanées : la seconde échoue sur le verrou du lot ou du stock (rejouée, puis refusée car le
lot est déjà annulé).
"""

from app.application.imports.cancel.blocking import BlockingFinder
from app.application.imports.cancel.withdraw import Withdrawal, withdraw_items
from app.application.imports.ports import ImportBatchRepository
from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWorkFactory
from app.application.security.actor import Actor
from app.application.security.permissions import Permission
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of
from app.application.stock.ledger import StockLedger
from app.application.stock.retry import with_stock_retry
from app.domain.imports.batch import ImportBatch
from app.domain.imports.errors import ImportCancelBlocked
from app.domain.imports.ids import ImportBatchId


class CancelImport:
    def __init__(self, uow_factory: UnitOfWorkFactory, policy: Policy, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._clock = clock
        self._ledger = StockLedger(clock)

    def execute(self, actor: Actor, batch_id: ImportBatchId) -> ImportBatch:
        self._policy.require(actor, Permission.IMPORT_CANCEL)
        return with_stock_retry(lambda: self._attempt(actor, batch_id))

    def _attempt(self, actor: Actor, batch_id: ImportBatchId) -> ImportBatch:
        run = Withdrawal(
            performer=performer_of(actor), now=self._clock.now(), today=self._clock.today()
        )
        with self._uow_factory(actor_shop(actor)) as uow:
            batches = ImportBatchRepository.within(uow)
            batch = batches.get(batch_id)
            batch.cancel(performer=run.performer, now=run.now)
            blocking = BlockingFinder(uow, batch).find()
            if blocking:
                raise ImportCancelBlocked(blocking)
            withdraw_items(uow, self._ledger, batch, run)
            batches.update(batch)
            uow.commit()
        return batch
