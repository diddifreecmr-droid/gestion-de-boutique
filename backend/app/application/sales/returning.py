"""Saisie d'un retour → éléments vérifiés dans la transaction (UC-VEN-09, EXC-01/02).

- `ReturnLineInput` : ligne de la vente (position 1 = première), quantité, état de retour en
  stock (Vendable par défaut), châssis rendus. Une ligne citée deux fois → 400.
- `returned_lines` : lignes rendues aux conditions de la vente d'origine (`return_lines.py`),
  compte tenu de **tous** les retours précédents de la vente.
- `checked_refund` : mode de paiement actif ; date facultative (aujourd'hui), jamais dans le
  futur ni avant la vente (RG-T09, propriétaire).
- `post_entries` : un « Retour client » par ligne rendue, au lieu de la vente, dans l'état
  choisi (grand livre, TR-12) ; source = le retour. Le CMP ne change pas (RG-T12).
- `release_returned` : châssis rendus libérés (RG-M01) : ils peuvent être revendus.
- `exchange_sale_input` : nouvelle vente d'un échange **à crédit** (décision client specs
  § 15.1) : client = celui de la vente d'origine, imposé (absent → `CustomerRequired` ; un
  autre client → 400). Les règles du crédit (acompte, plafond) sont celles de `RecordSale`.
- `require_no_returns` : une vente qui a un retour ne se modifie ni ne s'annule plus
  (`INVALID_STATE_TRANSITION`) — ses lignes, prix et châssis sont la base des retours.
"""

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from app.application.ports.uow import UnitOfWork
from app.application.sales.inputs import CustomerInput, SaleInput
from app.application.sales.ports import ChassisClaimRepository
from app.application.sales.return_ports import SaleReturnRepository
from app.application.shops.ports import PaymentModeRepository
from app.application.stock.ledger import StockLedger
from app.application.stock.postings import Posting
from app.domain.sales.errors import CustomerRequired
from app.domain.sales.return_lines import (
    AlreadyReturned,
    ReturnedLine,
    already_returned,
    returned_line,
)
from app.domain.sales.sale import Sale
from app.domain.sales.sale_return import Refund, SaleReturn
from app.domain.sales.values import SaleKind
from app.domain.shared.business_day import validate_entry_date
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed
from app.domain.shared.money import Money
from app.domain.shops.ids import PaymentModeId
from app.domain.stock.values import MovementType, SourceRef, SourceType, StockCondition


@dataclass(frozen=True, slots=True, kw_only=True)
class ReturnLineInput:
    line: int
    quantity: Decimal | int | str
    condition: StockCondition = StockCondition.SELLABLE
    chassis: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class RefundInput:
    amount: int
    mode_id: PaymentModeId
    refunded_on: date | None = None


def returned_lines(
    sale: Sale, wanted: tuple[ReturnLineInput, ...], previous: list[SaleReturn]
) -> list[ReturnedLine]:
    done = already_returned([line for ret in previous for line in ret.lines])
    positions = [item.line for item in wanted]
    if len(set(positions)) != len(positions):
        msg = "Une ligne de la vente est citée deux fois dans le retour"
        raise ValidationFailed(msg, details={"field": "lines.line"})
    lines = []
    for item in wanted:
        if not 1 <= item.line <= len(sale.content.lines):
            msg = "Ligne inconnue sur cette vente"
            raise ValidationFailed(msg, details={"field": "lines.line", "line": item.line})
        sold = sale.content.lines[item.line - 1]
        lines.append(
            returned_line(
                sold,
                item.line,
                item.quantity,
                item.condition,
                done.get(item.line, AlreadyReturned()),
                item.chassis,
            )
        )
    return lines


def active_mode(uow: UnitOfWork, mode_id: PaymentModeId) -> PaymentModeId:
    mode = PaymentModeRepository.within(uow).get(mode_id)
    if not mode.details.active:
        msg = "Mode de paiement désactivé : choisissez-en un autre"
        raise ValidationFailed(msg, details={"field": "refund.mode_id"})
    return mode.id


def checked_refund(uow: UnitOfWork, sale: Sale, wanted: RefundInput, today: date) -> Refund:
    on = validate_entry_date(wanted.refunded_on or today, today, is_owner=True)
    if on < sale.content.sold_on:
        msg = "Remboursement daté d'avant la vente"
        raise ValidationFailed(msg, details={"field": "refund.refunded_on"})
    return Refund(
        amount=Money.entry(wanted.amount, "refund.amount"),
        mode_id=active_mode(uow, wanted.mode_id),
        refunded_on=on,
    )


def post_entries(uow: UnitOfWork, ledger: StockLedger, sale: Sale, made: SaleReturn) -> None:
    source = SourceRef(SourceType.RETURN, made.id.value, str(sale.number))
    for line in made.lines:
        ledger.record_entry(
            uow,
            Posting(
                article_id=line.article_id,
                location_id=sale.location_id,
                type=MovementType.CUSTOMER_RETURN,
                quantity=line.stock_quantity,
                source=source,
                occurred_at=made.returned_at,
                author_id=made.created_by,
                condition=line.condition,
            ),
        )


def release_returned(uow: UnitOfWork, made: SaleReturn) -> None:
    keys = {key for line in made.lines for key in line.chassis}
    claims = ChassisClaimRepository.within(uow)
    for claim in claims.for_sale(made.sale_id):
        if claim.active and claim.key in keys:
            claim.release()
            claims.update(claim)


def require_no_returns(uow: UnitOfWork, sale: Sale) -> None:
    count = len(SaleReturnRepository.within(uow).for_sale(sale.id))
    if count:
        msg = "Cette vente a un retour : elle ne se modifie ni ne s'annule plus"
        raise InvalidStateTransition(msg, details={"returns": count})


def exchange_sale_input(sale: Sale, data: SaleInput) -> SaleInput:
    """Nouvelle vente d'un échange : lieu d'origine par défaut, client d'origine si à crédit."""
    if data.location_id is None:
        data = replace(data, location_id=sale.location_id)
    if data.kind is not SaleKind.CREDIT:
        return data
    customer_id = sale.content.customer_id
    if customer_id is None:
        raise CustomerRequired
    wanted = data.customer
    if wanted is not None and wanted.customer_id != customer_id:
        msg = "Échange à crédit : le client est celui de la vente d'origine"
        raise ValidationFailed(msg, details={"field": "exchange.sale.customer"})
    return replace(data, customer=CustomerInput(customer_id=customer_id))
