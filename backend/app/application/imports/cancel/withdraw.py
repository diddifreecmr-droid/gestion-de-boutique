"""Retrait de ce qu'un lot a créé (décision client QC-6) : **rien n'est effacé**.

Appelé dans l'unité de travail de l'annulation, une fois les blocages écartés, sans `commit` :

1. chaque « Reprise de départ » est **contrepassée** par un mouvement « Annulation » (document
   lié : le lot, `IMP-…`) ; les coûts des articles touchés sont rejoués d'après le grand livre
   (`refresh_costs` : CMP et dernier coût d'avant l'import) ;
2. articles créés : archivés, nom et référence libérés (`Article.withdraw`) ;
3. créances reprises : annulées (`cancel_with_import`) ;
4. clients et fournisseurs créés : désactivés, téléphone ou nom libéré (`withdraw`).

Chaque retrait est journalisé par l'événement de son agrégat, dans la même transaction.
"""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from app.application.catalog.ports import ArticleRepository
from app.application.ports.uow import UnitOfWork
from app.application.purchasing.costs import refresh_costs
from app.application.purchasing.ports import SupplierRepository
from app.application.receivables.ports import ReceivableRepository
from app.application.sales.ports import CustomerRepository
from app.application.stock.ledger import StockLedger
from app.domain.audit.values import Performer
from app.domain.catalog.ids import ArticleId
from app.domain.imports.batch import ImportBatch
from app.domain.imports.values import ImportedEntity
from app.domain.purchasing.ids import SupplierId
from app.domain.receivables.ids import ReceivableId
from app.domain.sales.ids import CustomerId
from app.domain.stock.ids import StockMovementId
from app.domain.stock.values import SourceRef, SourceType


@dataclass(frozen=True, slots=True, kw_only=True)
class Withdrawal:
    performer: Performer
    now: datetime
    today: date


def withdraw_items(
    uow: UnitOfWork, ledger: StockLedger, batch: ImportBatch, run: Withdrawal
) -> None:
    def ids(entity: ImportedEntity) -> list[UUID]:
        return [item.entity_id for item in batch.items if item.entity is entity]

    source = SourceRef(SourceType.IMPORT, batch.id.value, str(batch.number))
    touched: list[ArticleId] = []
    for movement_id in ids(ImportedEntity.STOCK_MOVEMENT):
        reversal = ledger.reverse(
            uow, StockMovementId(movement_id), source=source,
            author_id=run.performer.user_id, occurred_at=run.now,
        )  # fmt: skip
        touched.append(reversal.article_id)
    refresh_costs(uow, touched)
    articles = ArticleRepository.within(uow)
    for article_id in ids(ImportedEntity.ARTICLE):
        article = articles.get(ArticleId(article_id))
        article.withdraw(performer=run.performer, now=run.now)
        articles.update(article)
    receivables = ReceivableRepository.within(uow)
    for receivable_id in ids(ImportedEntity.RECEIVABLE):
        receivable = receivables.get(ReceivableId(receivable_id))
        receivable.cancel_with_import(
            number=str(batch.number), performer=run.performer, on=run.today, at=run.now
        )
        receivables.update(receivable)
    customers = CustomerRepository.within(uow)
    for customer_id in ids(ImportedEntity.CUSTOMER):
        customer = customers.get(CustomerId(customer_id))
        customer.withdraw(performer=run.performer, now=run.now)
        customers.update(customer)
    suppliers = SupplierRepository.within(uow)
    for supplier_id in ids(ImportedEntity.SUPPLIER):
        supplier = suppliers.get(SupplierId(supplier_id))
        supplier.withdraw(performer=run.performer, now=run.now)
        suppliers.update(supplier)
