"""Saisie d'un achat → `PurchaseDetails` vérifiés et chiffrés (UC-ACH-01, UC-ACH-03).

Commun à `RecordPurchase` et `CorrectPurchase` :

- date : aujourd'hui par défaut, contrôlée par `validate_entry_date` (RG-T09 : comptable J-7) ;
- lieu de réception : absent → **réglage de la boutique** `reception_location_id` (Q-01 :
  Garoua au Lot 1) ; lu dans la boutique (autre boutique → 404) et actif ;
- fournisseur : facultatif, lu dans la boutique et actif ;
- article : lu dans la boutique, actif (un article archivé sort des listes d'achat) ; unité
  saisie absente → unité de stock de l'article ; conversion RG-X02 (`to_stock_quantity`) ;
- lors d'une correction, un lieu, un fournisseur ou un article **inchangé** peut être devenu
  inactif : la correction reste possible.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.application.catalog.ports import ArticleRepository
from app.application.ports.uow import UnitOfWork
from app.application.purchasing.ports import SupplierRepository
from app.application.shops.ports import LocationRepository, ShopSettingsRepository
from app.domain.catalog.article import Article
from app.domain.catalog.ids import ArticleId, AttachmentId
from app.domain.purchasing.ids import SupplierId
from app.domain.purchasing.lines import CostedLine, FeeKind, PurchaseFee, PurchaseLine, cost_lines
from app.domain.purchasing.purchase import Purchase
from app.domain.purchasing.units import EntryUnit, entered_quantity, to_stock_quantity
from app.domain.purchasing.values import PurchaseDetails
from app.domain.shared.business_day import validate_entry_date
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.money import Money
from app.domain.shops.ids import LocationId


@dataclass(frozen=True, slots=True, kw_only=True)
class LineInput:
    article_id: ArticleId
    quantity: Decimal | int | str
    unit_price: int
    unit: EntryUnit | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class FeeInput:
    kind: FeeKind
    amount: int
    label: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class PurchaseInput:
    lines: tuple[LineInput, ...]
    fees: tuple[FeeInput, ...] = ()
    purchase_date: date | None = None
    location_id: LocationId | None = None
    supplier_id: SupplierId | None = None
    invoice_ref: str | None = None
    invoice_photo_id: AttachmentId | None = None
    note: str | None = None


def inactive(field: str) -> ValidationFailed:
    return ValidationFailed("Élément désactivé : choisissez-en un autre", details={"field": field})


class PurchaseResolver:
    def __init__(
        self, uow: UnitOfWork, *, today: date, is_owner: bool, previous: Purchase | None = None
    ) -> None:
        self._uow = uow
        self._today = today
        self._is_owner = is_owner
        self._previous = None if previous is None else previous.details
        self.articles: dict[ArticleId, Article] = {}

    def resolve(self, data: PurchaseInput) -> tuple[PurchaseDetails, tuple[CostedLine, ...]]:
        on = data.purchase_date or self._today
        validate_entry_date(on, self._today, is_owner=self._is_owner)
        lines = tuple(self._line(item) for item in data.lines)
        details = PurchaseDetails(
            purchase_date=on,
            location_id=self._location(data.location_id),
            lines=lines,
            fees=tuple(
                PurchaseFee(
                    kind=fee.kind, amount=Money.entry(fee.amount, "fees.amount"), label=fee.label
                )
                for fee in data.fees
            ),
            supplier_id=self._supplier(data.supplier_id),
            invoice_ref=data.invoice_ref,
            invoice_photo_id=data.invoice_photo_id,
            note=data.note,
        )
        quantities = []
        for line in lines:
            fields = self.articles[line.article_id].details.fields
            quantities.append(
                to_stock_quantity(
                    line.quantity, line.unit, fields.stock_unit, fields.piece_length_m
                )
            )
        return details, cost_lines(lines, quantities, details.fees)

    def _location(self, wanted: LocationId | None) -> LocationId:
        if wanted is None:
            wanted = ShopSettingsRepository.within(self._uow).current().values.reception_location_id
            if wanted is None:
                msg = "Lieu de réception obligatoire (aucun lieu par défaut réglé)"
                raise ValidationFailed(msg, details={"field": "location_id"})
        location = LocationRepository.within(self._uow).get(wanted)
        unchanged = self._previous is not None and self._previous.location_id == wanted
        if not location.active and not unchanged:
            raise inactive("location_id")
        return location.id

    def _supplier(self, wanted: SupplierId | None) -> SupplierId | None:
        if wanted is None:
            return None
        supplier = SupplierRepository.within(self._uow).get(wanted)
        unchanged = self._previous is not None and self._previous.supplier_id == wanted
        if not supplier.active and not unchanged:
            raise inactive("supplier_id")
        return supplier.id

    def _line(self, item: LineInput) -> PurchaseLine:
        article = ArticleRepository.within(self._uow).get(item.article_id)
        before = () if self._previous is None else self._previous.lines
        if not article.is_active and all(line.article_id != article.id for line in before):
            raise inactive("lines.article_id")
        self.articles[article.id] = article
        unit = item.unit or EntryUnit(article.details.fields.stock_unit.value)
        price = Money.entry(item.unit_price, "lines.unit_price")
        return PurchaseLine(
            article_id=article.id,
            quantity=entered_quantity(item.quantity, unit),
            unit=unit,
            unit_price=price,
        )
