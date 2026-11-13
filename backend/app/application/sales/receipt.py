"""DTO du reçu de vente (UC-VEN-04, TR-18, RCP-01) : rendu côté client, jamais de coût.

Contenu : en-tête de la boutique (nom, ville, téléphone, adresse, NIU et RCCM s'ils sont
renseignés, logo affiché ou non), « Reçu de vente », numéro (et numéro provisoire), date et
heure, vendeur (avec le libellé du rôle selon le profil : « Vendeur » en Motos,
« Employé » en Prêt-à-porter et Textile), client (nom, téléphone), lignes (article, détails
couleur / châssis / moteur / taille, quantité et son libellé « 2,5 m » / « 1 pièce (5,49 m) »,
prix unitaire, total),
totaux (total, payé **par mode**, reste à payer), mentions (« Vente à crédit », « Annulé »,
« Duplicata »), message de pied et réglages d'impression. **Aucun** coût, CMP ni marge, même
pour le propriétaire (RG-D02, SEC-N04) : le DTO ne les porte pas, il n'y a rien à filtrer.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType

from app.domain.catalog.ids import ArticleId
from app.domain.profiles.registry import profile_for
from app.domain.sales.customer import Customer
from app.domain.sales.lines import SaleMode, SoldDetail
from app.domain.sales.quantity_label import quantity_label, sold_piece_length
from app.domain.sales.sale import Sale
from app.domain.sales.values import SaleKind, SaleStatus
from app.domain.shared.roles import Role
from app.domain.shops.ids import PaymentModeId
from app.domain.shops.payment_mode import PaymentMode
from app.domain.shops.settings import SettingsValues
from app.domain.shops.shop import Shop

RECEIPT_TITLE = "Reçu de vente"


class Mention(StrEnum):
    CREDIT_SALE = "credit_sale"  # « Vente à crédit »
    CANCELLED = "cancelled"  # « Annulé »
    DUPLICATE = "duplicate"  # « Duplicata »

    @property
    def label(self) -> str:
        return {"credit_sale": "Vente à crédit", "cancelled": "Annulé", "duplicate": "Duplicata"}[
            self.value
        ]


@dataclass(frozen=True, slots=True)
class ReceiptLine:
    article_name: str
    sale_mode: SaleMode
    quantity: Decimal
    unit_price: int
    line_total: int
    details: tuple[SoldDetail, ...]
    quantity_label: str
    """« 2 », « 2,5 m », « 1 pièce (5,49 m) » (TEX-06)."""


@dataclass(frozen=True, slots=True)
class ReceiptPayment:
    mode_name: str
    amount: int
    reference: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class Receipt:
    shop: Shop
    settings: SettingsValues
    sale: Sale
    seller_name: str
    seller_role_label: str
    """« Vendeur » (Motos) ou « Employé » (Prêt-à-porter, Textile) : « Vendeur : Ali »."""
    customer: Customer | None
    lines: tuple[ReceiptLine, ...]
    payments: tuple[ReceiptPayment, ...]
    mentions: tuple[Mention, ...]
    print_sequence: int
    printed_at: datetime
    title: str = RECEIPT_TITLE


def build_receipt(
    *,
    shop: Shop,
    settings: SettingsValues,
    sale: Sale,
    seller_name: str,
    customer: Customer | None,
    modes: Mapping[PaymentModeId, PaymentMode],
    sequence: int,
    printed_at: datetime,
    piece_lengths: Mapping[ArticleId, Decimal | None] = MappingProxyType({}),
) -> Receipt:
    """`piece_lengths` : longueur actuelle de la pièce des articles vendus « à la pièce »."""
    mentions = []
    if sale.kind is SaleKind.CREDIT:
        mentions.append(Mention.CREDIT_SALE)
    if sale.status is SaleStatus.CANCELLED:
        mentions.append(Mention.CANCELLED)
    if sequence > 1:
        mentions.append(Mention.DUPLICATE)
    lines = tuple(
        ReceiptLine(
            article_name=line.article_name,
            sale_mode=line.sale_mode,
            quantity=line.quantity,
            unit_price=line.unit_price.amount,
            line_total=line.line_total.amount,
            details=line.details,
            quantity_label=quantity_label(
                line.sale_mode,
                line.quantity,
                sold_piece_length(line, piece_lengths.get(line.article_id)),
            ),
        )
        for line in sale.content.lines
    )
    payments = tuple(
        ReceiptPayment(modes[p.mode_id].name, p.amount.amount, p.reference)
        for p in sale.content.payments
    )
    return Receipt(
        shop=shop,
        settings=settings,
        sale=sale,
        seller_name=seller_name,
        seller_role_label=profile_for(shop.profile_code).role_label(Role.SELLER),
        customer=customer,
        lines=lines,
        payments=payments,
        mentions=tuple(mentions),
        print_sequence=sequence,
        printed_at=printed_at,
    )
