"""Monde de test de l'annulation des lots (T35, QC-6) : `FlowWorld` + lectures et opérations
qui « touchent » un lot.

`sell` pose une sortie « Sortie vente » au grand livre, comme le ferait la vente `V-…` (le
blocage regarde le grand livre, pas l'écran de vente) ; `owned(phone)` lit le client qui occupe
un téléphone.
"""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.application.catalog.ports import ARTICLE_NAME, ArticleRepository
from app.application.sales.ports import CustomerRepository
from app.application.security.actor import Actor
from app.application.shops.ports import LocationRepository
from app.application.stock.ledger import StockLedger
from app.application.stock.postings import Posting
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId
from app.domain.catalog.keys import identity_key
from app.domain.identity.phone import PhoneNumber
from app.domain.imports.batch import ImportBatch
from app.domain.sales.customer import Customer
from app.domain.shared.ids import uuid7
from app.domain.shared.quantity import Quantity
from app.domain.stock.values import MovementType, SourceRef, SourceType
from tests.application.imports.flows import FlowWorld

ARTICLES = "Nom\nPantalon\nBoubou\n"
STOCK = "Article;Lieu;Quantité;Coût unitaire\nPantalon;Boutique;10;9 000\n"


@dataclass
class CancelWorld(FlowWorld):
    def cancel(self, actor: Actor, batch: ImportBatch) -> ImportBatch:
        return self.imports.http.cancel.execute(actor, batch.id)

    def reload(self, actor: Actor, batch: ImportBatch) -> ImportBatch:
        return self.imports.http.read.get(actor, batch.id).batch

    def article(self, actor: Actor, article_id: UUID) -> Article:
        with self.core.shop_uow_factory(self.shop_of(actor)) as uow:
            return ArticleRepository.within(uow).get(ArticleId(article_id))

    def named(self, actor: Actor, name: str) -> Article | None:
        with self.core.shop_uow_factory(self.shop_of(actor)) as uow:
            return ArticleRepository.within(uow).find_by_key(ARTICLE_NAME, identity_key(name))

    def owned(self, actor: Actor, phone: str) -> Customer | None:
        with self.core.shop_uow_factory(self.shop_of(actor)) as uow:
            return CustomerRepository.within(uow).find_by_phone(PhoneNumber.parse(phone))

    def sell(self, owner: Actor, name: str, number: str, quantity: int = 1) -> None:
        found = self.named(owner, name)
        assert found is not None
        with self.core.shop_uow_factory(self.shop_of(owner)) as uow:
            [place] = [p for p in LocationRepository.within(uow).list_all() if p.name == "Boutique"]
            posting = Posting(
                article_id=found.id, location_id=place.id, type=MovementType.SALE_OUT,
                quantity=Quantity.of(Decimal(quantity), found.details.fields.stock_unit),
                source=SourceRef(SourceType.SALE, uuid7(), number),
                occurred_at=self.clock.now(), author_id=owner.user_id,
            )  # fmt: skip
            StockLedger(self.clock).record_exit(uow, posting)
            uow.commit()
