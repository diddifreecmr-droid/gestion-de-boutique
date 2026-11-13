"""UC-VEN-04 — Imprimer ou partager un reçu : `GET /sales/{id}/receipt` (RCP-01 à RCP-03).

Chaque demande **est** une impression : elle est inscrite (`ReceiptPrint`, journal « Imprimer »)
avec son rang ; dès la 2ᵉ, le reçu porte « Duplicata » (Q-25 tranchée). Le reçu d'une vente
annulée porte « Annulé ». Portée : le vendeur ne lit que les reçus de ses ventes (404 sinon) ;
comptable et chauffeur : 403 (RG-D03). Le nom du vendeur vient du compte (plateforme).
Lignes « à la pièce » : la longueur de la pièce est relue sur l'article (`quantity_label.py`).
"""

from decimal import Decimal

from app.application.catalog.ports import ArticleRepository
from app.application.identity.uow import IdentityUnitOfWorkFactory
from app.application.ports.clock import Clock
from app.application.ports.repository import not_found
from app.application.ports.uow import UnitOfWork, UnitOfWorkFactory
from app.application.sales.ports import CustomerRepository, ReceiptPrintRepository, SaleRepository
from app.application.sales.receipt import Receipt, build_receipt
from app.application.sales.retry import with_sale_retry
from app.application.sales.use_cases.read_sales import seller_scope
from app.application.security.actor import Actor
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of
from app.application.shops.ports import (
    PaymentModeRepository,
    ShopRepository,
    ShopSettingsRepository,
)
from app.domain.catalog.ids import ArticleId
from app.domain.sales.ids import SaleId
from app.domain.sales.lines import SaleMode
from app.domain.sales.receipt_print import ReceiptPrint
from app.domain.sales.sale import Sale
from app.domain.shared.ids import UserId


class GetReceipt:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        platform: IdentityUnitOfWorkFactory,
        policy: Policy,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._platform = platform
        self._policy = policy
        self._clock = clock

    def execute(self, actor: Actor, sale_id: SaleId) -> Receipt:
        seller = seller_scope(self._policy, actor)
        return with_sale_retry(lambda: self._attempt(actor, sale_id, seller))

    def _seller_name(self, user_id: UserId) -> str:
        with self._platform() as uow:
            return uow.users.get(user_id).name

    def _attempt(self, actor: Actor, sale_id: SaleId, seller: UserId | None) -> Receipt:
        now = self._clock.now()
        with self._uow_factory(actor_shop(actor)) as uow:
            sale = SaleRepository.within(uow).get(sale_id)
            if seller is not None and sale.seller_id != seller:
                raise not_found(sale_id)
            prints = ReceiptPrintRepository.within(uow)
            sequence = prints.count_for(sale.id) + 1
            prints.add(
                ReceiptPrint.record(
                    uow.shop_id, sale.entity, sequence, performer=performer_of(actor), now=now
                )
            )
            customer_id = sale.content.customer_id
            customer = (
                None if customer_id is None else CustomerRepository.within(uow).get(customer_id)
            )
            modes = {mode.id: mode for mode in PaymentModeRepository.within(uow).list_all()}
            shop = ShopRepository.within(uow).current()
            settings = ShopSettingsRepository.within(uow).current().values
            lengths = _piece_lengths(uow, sale)
            uow.commit()
        return build_receipt(
            shop=shop,
            settings=settings,
            sale=sale,
            seller_name=self._seller_name(sale.seller_id),
            customer=customer,
            modes=modes,
            sequence=sequence,
            printed_at=now,
            piece_lengths=lengths,
        )


def _piece_lengths(uow: UnitOfWork, sale: Sale) -> dict[ArticleId, Decimal | None]:
    articles = ArticleRepository.within(uow)
    wanted = {line.article_id for line in sale.content.lines if line.sale_mode is SaleMode.PIECE}
    return {ident: articles.get(ident).details.fields.piece_length_m for ident in wanted}
