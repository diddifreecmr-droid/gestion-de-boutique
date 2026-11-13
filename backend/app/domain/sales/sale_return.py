"""Agrégat `SaleReturn` : retour ou échange sur une vente (UC-VEN-09, SCN-05, EXC-01/02).

- Vente d'origine **valide** (une vente annulée → `INVALID_STATE_TRANSITION`), lignes rendues
  (`return_lines.py`), motif obligatoire, instant du retour : la valeur et la marge du retour
  comptent **le jour du retour** (`returned_on`, § 14.1) ; la journée de la vente ne change pas.
- **Argent (Q-05 tranché, `settlement`)** :
  - vente à crédit : la valeur rendue baisse d'abord la créance de la vente
    (`credit_reduction` = min(valeur, reste dû de la vente non encore baissé)) →
    `CreditSaleReturned` (T17) ; le surplus éventuel peut être remboursé (acompte) ;
  - remboursement (`refund` : montant, mode, date) ≤ valeur rendue - baisse de créance, et
    ≤ payé à la vente - remboursements précédents (`OVERPAYMENT`). Il peut être inférieur à la
    valeur rendue (750 000 pour 780 000) ou absent ;
  - **échange** : le remboursement vaut **toute** la part non imputée sur la créance (avoir) ;
    la nouvelle vente (`exchange_sale_id`) reçoit un paiement du même mode et du même montant
    (plafonné à son total). Seule la différence circule donc réellement : argent encaissé du
    jour = paiements - remboursements (RG-T21).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

from app.domain.audit.values import EntityRef, Performer
from app.domain.purchasing.rules import clean_reason
from app.domain.sales import events as ev
from app.domain.sales.errors import RefundOverpayment
from app.domain.sales.ids import SaleId, SaleReturnId
from app.domain.sales.receivable_events import CreditSaleReturned
from app.domain.sales.return_lines import ReturnedLine
from app.domain.sales.sale import Sale
from app.domain.sales.values import MAX_LINES, SaleKind
from app.domain.shared.business_day import business_date, require_aware
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId, UserId
from app.domain.shared.money import Money
from app.domain.shops.ids import PaymentModeId


class ReturnKind(StrEnum):
    RETURN = "return"  # Retour simple
    EXCHANGE = "exchange"  # Échange


@dataclass(frozen=True, slots=True, kw_only=True)
class Refund:
    amount: Money
    mode_id: PaymentModeId
    refunded_on: date

    def __post_init__(self) -> None:
        if self.amount.amount <= 0:
            msg = "Le montant remboursé doit être supérieur à 0"
            raise ValidationFailed(msg, details={"field": "refund.amount"})


@dataclass(frozen=True, slots=True)
class Settlement:
    credit_reduction: Money
    refund_max: Money


def settlement(sale: Sale, value: Money, previous: Sequence["SaleReturn"]) -> Settlement:
    """Baisse de créance et remboursement maximal d'un nouveau retour de valeur `value`."""
    reduction = Money.zero()
    if sale.kind is SaleKind.CREDIT:
        outstanding = sale.remaining - Money.total(r.credit_reduction for r in previous)
        reduction = max(Money.zero(), min(value, outstanding))
    refundable = sale.paid - Money.total(r.refunded for r in previous)
    return Settlement(reduction, max(Money.zero(), min(value - reduction, refundable)))


def _sum(values: Sequence[Money | None]) -> Money | None:
    known = [value for value in values if value is not None]
    return None if len(known) != len(values) else Money.total(known)


@dataclass(eq=False, kw_only=True)
class SaleReturn:
    id: SaleReturnId
    shop_id: ShopId
    sale_id: SaleId
    sale_number: str
    kind: ReturnKind
    lines: tuple[ReturnedLine, ...]
    reason: str
    returned_at: datetime
    created_by: UserId
    refund: Refund | None = None
    credit_reduction: Money = field(default_factory=Money.zero)
    exchange_sale_id: SaleId | None = None
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.kind = ReturnKind(self.kind)
        self.returned_at = require_aware(self.returned_at)
        self.lines = tuple(self.lines)
        if not 1 <= len(self.lines) <= MAX_LINES:
            msg = f"Un retour compte de 1 à {MAX_LINES} lignes"
            raise ValidationFailed(msg, details={"field": "lines"})
        if (self.kind is ReturnKind.EXCHANGE) != (self.exchange_sale_id is not None):
            msg = "Un échange, et lui seul, porte la nouvelle vente"
            raise ValueError(msg)

    # ------------------------------------------------------------------ lectures
    @property
    def returned_on(self) -> date:
        """Journée (Douala) où le retour compte dans les ventes, la marge et l'encaissé."""
        return business_date(self.returned_at)

    @property
    def amount(self) -> Money:
        return Money.total(line.amount for line in self.lines)

    @property
    def margin(self) -> Money | None:
        return _sum([line.margin for line in self.lines])

    @property
    def margin_wac(self) -> Money | None:
        return _sum([line.margin_wac for line in self.lines])

    @property
    def refunded(self) -> Money:
        return Money.zero() if self.refund is None else self.refund.amount

    @property
    def entity(self) -> EntityRef:
        return EntityRef("sale", self.sale_id.value, self.sale_number)

    # ------------------------------------------------------------------ création
    @classmethod
    def record(
        cls,
        sale: Sale,
        lines: Sequence[ReturnedLine],
        *,
        reason: str,
        previous: Sequence["SaleReturn"],
        refund: Refund | None,
        performer: Performer,
        now: datetime,
        exchange_sale_id: SaleId | None = None,
        return_id: SaleReturnId | None = None,
        late: bool = False,
    ) -> "SaleReturn":
        sale.require_valid()
        kind = ReturnKind.RETURN if exchange_sale_id is None else ReturnKind.EXCHANGE
        made = cls(
            id=return_id or SaleReturnId.new(),
            shop_id=sale.shop_id,
            sale_id=sale.id,
            sale_number=str(sale.number),
            kind=kind,
            lines=tuple(lines),
            reason=clean_reason(reason),
            returned_at=now,
            created_by=performer.user_id,
            exchange_sale_id=exchange_sale_id,
        )
        settled = settlement(sale, made.amount, previous)
        if refund is not None and refund.amount > settled.refund_max:
            raise RefundOverpayment(refund=refund.amount, maximum=settled.refund_max)
        made.refund, made.credit_reduction = refund, settled.credit_reduction
        if late and exchange_sale_id is None:
            msg = "Seul un échange peut être hors délai"
            raise ValueError(msg)
        label = "Échange" if exchange_sale_id is not None else "Retour"
        label += " hors délai" if late else ""
        event = ev.SaleExchangedLate if late else ev.SaleReturnRecorded
        made.events.record(
            event(
                shop_id=sale.shop_id,
                occurred_at=now,
                performer=performer,
                entity=made.entity,
                summary=f"{label} sur la vente {sale.number} : {made.amount}"[:500],
                reason=made.reason,
            )
        )
        if made.credit_reduction.amount > 0:
            made.events.record(
                CreditSaleReturned(
                    shop_id=sale.shop_id,
                    occurred_at=now,
                    sale_id=sale.id,
                    amount=made.credit_reduction,
                )
            )
        return made
