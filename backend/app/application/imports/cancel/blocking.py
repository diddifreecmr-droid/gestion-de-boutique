"""Ce qui empêche d'annuler un lot (décision client QC-6) : lecture seule, dans l'unité de
travail de l'annulation.

Par élément du lot :

- **article** créé : tout mouvement de son grand livre qui n'est pas du lot (vente, retour,
  achat, ajustement, inventaire, stock de départ d'un autre lot encore importé) ; tout
  inventaire lancé depuis l'import qui le compte (même sans écart, abandonné excepté) ;
- **stock de départ** (mouvement « Reprise de départ ») : les mêmes opérations sur le même
  article **au même lieu**, enregistrées depuis l'import ;
- **client** créé : toute vente (annulée comprise), toute créance qui n'est pas du lot (créance
  d'une vente : déjà citée par sa vente ; créance ancienne d'un autre lot : ce lot) ;
- **créance** reprise : tout versement valide (`R-…`) ;
- **fournisseur** créé : tout achat (annulé compris).

Un stock de départ d'un lot **déjà annulé** (mouvement contrepassé) et sa contrepassation ne
bloquent jamais : l'annulation dans l'ordre inverse des imports reste possible.
"""

from datetime import datetime
from uuid import UUID

from app.application.imports.ports import ImportBatchRepository
from app.application.ports.uow import UnitOfWork
from app.application.purchasing.ports import PurchaseRepository
from app.application.receivables.ports import ReceivableRepository
from app.application.sales.ports import SaleRepository
from app.application.stock.ports import InventoryRepository, StockMovementLog
from app.domain.catalog.ids import ArticleId
from app.domain.imports.batch import ImportBatch
from app.domain.imports.blocking import BlockingOperation, BlockingType
from app.domain.imports.values import ImportedEntity, ImportStatus
from app.domain.purchasing.ids import SupplierId
from app.domain.receivables.ids import ReceivableId
from app.domain.receivables.values import ReceivableOrigin, ReceivableStatus
from app.domain.sales.ids import CustomerId
from app.domain.shared.business_day import business_date
from app.domain.shops.ids import LocationId
from app.domain.stock.ids import StockMovementId
from app.domain.stock.inventory import InventoryStatus
from app.domain.stock.movement import StockMovement
from app.domain.stock.values import MovementType, SourceType

_BY_SOURCE = {
    SourceType.SALE: BlockingType.SALE,
    SourceType.RETURN: BlockingType.SALE_RETURN,
    SourceType.PURCHASE: BlockingType.PURCHASE,
    SourceType.ADJUSTMENT: BlockingType.ADJUSTMENT,
    SourceType.INVENTORY: BlockingType.INVENTORY,
    SourceType.IMPORT: BlockingType.IMPORT,
}
_UNNUMBERED = {BlockingType.ADJUSTMENT: "Ajustement"}


def _of_movement(movement: StockMovement) -> BlockingOperation:
    kind = _BY_SOURCE.get(movement.source.type)
    if kind is None:  # déplacements (Lot 2) : aucun mouvement de ce type ne peut exister ici
        msg = f"Mouvement de source inattendue : {movement.source.type}"
        raise RuntimeError(msg)
    number = movement.source.number
    if number is None:
        day = business_date(movement.occurred_at).strftime("%d/%m/%Y")
        number = f"{_UNNUMBERED.get(kind, kind.value)} du {day}"
    return BlockingOperation(kind, number)


class BlockingFinder:
    def __init__(self, uow: UnitOfWork, batch: ImportBatch) -> None:
        self._uow, self._batch = uow, batch
        self._log = StockMovementLog.within(uow)
        self._mine = {(item.entity, item.entity_id) for item in batch.items}
        self._found: set[BlockingOperation] = set()

    def find(self) -> list[BlockingOperation]:
        checks = {
            ImportedEntity.ARTICLE: self._article,
            ImportedEntity.STOCK_MOVEMENT: self._opening,
            ImportedEntity.CUSTOMER: self._customer,
            ImportedEntity.RECEIVABLE: self._receivable,
            ImportedEntity.SUPPLIER: self._supplier,
        }
        for item in self._batch.items:
            checks[item.entity](item.entity_id)
        return sorted(self._found)

    # ------------------------------------------------------------------ stock
    def _counts(self, movement: StockMovement) -> bool:
        """Le mouvement touche-t-il le lot ? Ni le lot lui-même, ni un lot déjà retiré."""
        source = movement.source
        if source.type is not SourceType.IMPORT:
            return True
        if source.id == self._batch.id.value:
            return False
        return movement.type is not MovementType.REVERSAL and (
            self._log.reversal_of(movement.id) is None
        )

    def _stock(self, article_id: ArticleId, location: LocationId | None, since: datetime) -> None:
        for movement in self._log.chronology(article_id):
            here = location is None or movement.location_id == location
            if here and movement.recorded_at >= since and self._counts(movement):
                self._found.add(_of_movement(movement))
        for inventory in InventoryRepository.within(self._uow).started_since(since):
            here = location is None or inventory.location_id == location
            counted = article_id in inventory.lines
            if here and counted and inventory.status is not InventoryStatus.ABANDONED:
                self._found.add(BlockingOperation(BlockingType.INVENTORY, str(inventory.number)))

    def _article(self, entity_id: UUID) -> None:
        self._stock(ArticleId(entity_id), None, self._batch.imported_at)

    def _opening(self, entity_id: UUID) -> None:
        movement = self._log.find(StockMovementId(entity_id))
        if movement is None:
            msg = f"Mouvement {entity_id} du lot {self._batch.number} introuvable"
            raise RuntimeError(msg)
        self._stock(movement.article_id, movement.location_id, movement.recorded_at)

    # ------------------------------------------------------------------ personnes
    def _customer(self, entity_id: UUID) -> None:
        customer_id = CustomerId(entity_id)
        for sale in SaleRepository.within(self._uow).for_customer(customer_id):
            self._found.add(BlockingOperation(BlockingType.SALE, str(sale.number)))
        for receivable in ReceivableRepository.within(self._uow).for_customer(customer_id):
            legacy = receivable.origin is ReceivableOrigin.LEGACY
            ours = (ImportedEntity.RECEIVABLE, receivable.id.value) in self._mine
            if ours or not legacy or receivable.status is ReceivableStatus.CANCELLED:
                continue  # créance d'une vente : déjà citée par sa vente
            other = ImportBatchRepository.within(self._uow).batch_of(
                ImportedEntity.RECEIVABLE, receivable.id.value
            )
            if other is not None and other.status is ImportStatus.IMPORTED:
                self._found.add(BlockingOperation(BlockingType.IMPORT, str(other.number)))
            else:
                label = receivable.entity.number or "Créance ancienne"
                self._found.add(BlockingOperation(BlockingType.RECEIVABLE, label))

    def _receivable(self, entity_id: UUID) -> None:
        receivable = ReceivableRepository.within(self._uow).get(ReceivableId(entity_id))
        for installment in receivable.installments:
            if installment.valid:
                number = str(installment.number)
                self._found.add(BlockingOperation(BlockingType.PAYMENT, number))

    def _supplier(self, entity_id: UUID) -> None:
        for purchase in PurchaseRepository.within(self._uow).for_supplier(SupplierId(entity_id)):
            self._found.add(BlockingOperation(BlockingType.PURCHASE, str(purchase.number)))
