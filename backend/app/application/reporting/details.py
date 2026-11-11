"""UC-TDB-04 — Listes qui expliquent chaque chiffre du tableau de bord.

Chaque liste a pour total **le chiffre affiché** (mêmes règles que `indicators.py`) :

- `sales` : ventes datées de la période (+ total), ventes annulées pendant la période (- total,
  Q-09), retours de la période (- montant) ; marge au dernier coût par ligne (`None` : non
  calculable, RG-T15). Total = ventes de la période.
- `payments` : argent encaissé **par mode de paiement** (comptant, acomptes, versements, moins
  annulations et remboursements, RG-T21). Total = argent encaissé.
- `expenses` : dépenses **par catégorie** (moins les annulations de la période). Total = dépenses.
- `receivables` : créances En cours, reste décroissant. Total = total à recevoir (état actuel).
- `low_stock` : articles sous le seuil (stock vendable tous lieux). Total = nombre d'articles.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.application.reporting.ports import ExpenseFlow, MoneyFlow
from app.domain.receivables.receivable import Receivable
from app.domain.sales.sale import Sale
from app.domain.sales.sale_return import SaleReturn
from app.domain.shared.business_day import business_date
from app.domain.shared.ids import EntityId
from app.domain.shared.money import Money
from app.domain.shops.ids import ExpenseCategoryId, PaymentModeId


class DetailMetric(StrEnum):
    SALES = "sales"
    PAYMENTS = "payments"
    EXPENSES = "expenses"
    RECEIVABLES = "receivables"
    LOW_STOCK = "low_stock"


class LineKind(StrEnum):
    SALE = "sale"
    CANCELLATION = "cancellation"
    RETURN = "return"
    PAYMENT_MODE = "payment_mode"
    EXPENSE_CATEGORY = "expense_category"
    RECEIVABLE = "receivable"
    ARTICLE = "article"


@dataclass(frozen=True, slots=True, kw_only=True)
class DetailLine:
    kind: LineKind
    id: UUID
    label: str
    day: date | None = None
    amount: int | None = None
    count: int | None = None
    margin: int | None = None
    quantity: Decimal | None = None
    threshold: Decimal | None = None


def sale_margin(sale: Sale) -> int | None:
    """Marge au dernier coût figé de la vente ; `None` si une ligne n'a pas de coût (RG-T15)."""
    margins = [line.margin for line in sale.content.lines]
    if any(m is None for m in margins):
        return None
    return Money.total(m for m in margins if m is not None).amount


def _negated(value: int | None) -> int | None:
    return None if value is None else -value


def sales_lines(
    sold: Iterable[Sale], cancelled: Iterable[Sale], returns: Iterable[SaleReturn]
) -> list[DetailLine]:
    lines = [
        DetailLine(
            kind=LineKind.SALE,
            id=s.id.value,
            label=str(s.number),
            day=s.content.sold_on,
            amount=s.total.amount,
            margin=sale_margin(s),
        )
        for s in sold
    ]
    for s in cancelled:
        if s.cancellation is None:  # exclu par le port : défense en profondeur
            msg = f"Vente {s.number} lue comme annulée sans annulation"
            raise RuntimeError(msg)
        lines.append(
            DetailLine(
                kind=LineKind.CANCELLATION,
                id=s.id.value,
                label=str(s.number),
                day=business_date(s.cancellation.at),
                amount=-s.total.amount,
                margin=_negated(sale_margin(s)),
            )
        )
    for r in returns:
        margin = None if r.margin is None else -r.margin.amount
        lines.append(
            DetailLine(
                kind=LineKind.RETURN,
                id=r.id.value,
                label=r.sale_number,
                day=r.returned_on,
                amount=-r.amount.amount,
                margin=margin,
            )
        )
    return lines


def by_mode(flows: Iterable[MoneyFlow], names: dict[PaymentModeId, str]) -> list[DetailLine]:
    amounts: dict[PaymentModeId, int] = defaultdict(int)
    counts: dict[PaymentModeId, int] = defaultdict(int)
    for flow in flows:
        amounts[flow.mode_id] += flow.signed
        counts[flow.mode_id] += flow.count
    return _ranked(LineKind.PAYMENT_MODE, amounts, counts, names)


def by_category(
    flows: Iterable[ExpenseFlow], names: dict[ExpenseCategoryId, str]
) -> list[DetailLine]:
    amounts: dict[ExpenseCategoryId, int] = defaultdict(int)
    counts: dict[ExpenseCategoryId, int] = defaultdict(int)
    for flow in flows:
        amounts[flow.category_id] += flow.signed
        counts[flow.category_id] += -flow.count if flow.cancelled else flow.count
    return _ranked(LineKind.EXPENSE_CATEGORY, amounts, counts, names)


def _ranked[K: EntityId](
    kind: LineKind, amounts: dict[K, int], counts: dict[K, int], names: dict[K, str]
) -> list[DetailLine]:
    missing = set(amounts) - set(names)
    if missing:
        msg = f"Référence inconnue dans les sommes : {sorted(str(m) for m in missing)}"
        raise RuntimeError(msg)
    shown = [k for k in amounts if amounts[k] or counts[k]]  # net nul : rien à expliquer
    keys = sorted(shown, key=lambda k: (-amounts[k], names[k], str(k)))
    return [
        DetailLine(kind=kind, id=k.value, label=names[k], amount=amounts[k], count=counts[k])
        for k in keys
    ]


def receivable_lines(open_: Iterable[Receivable], names: dict[UUID, str]) -> list[DetailLine]:
    ordered = sorted(open_, key=lambda r: (-r.remaining.amount, r.opened_on, r.id.value))
    return [
        DetailLine(
            kind=LineKind.RECEIVABLE,
            id=r.id.value,
            label=names[r.customer_id.value],
            day=r.opened_on,
            amount=r.remaining.amount,
        )
        for r in ordered
    ]
