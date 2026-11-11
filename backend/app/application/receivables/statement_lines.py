"""Relevé de compte d'un client (UC-CRE-05, REC-06) : opérations et reste dû après chacune.

| Opération | Effet sur le reste dû |
| --- | --- |
| `sale` (vente à crédit, total) | + total |
| `deposit` (acompte payé à la vente) | - acompte |
| `opening` (créance ancienne) | + montant repris |
| `installment` valide | - montant (0 s'il s'agit d'une récupération sur perte) |
| `installment` annulé | 0 (montré barré : le reste est recalculé, UC-CRE-08) |
| `write_off` (mise en perte) | - reste de la créance (elle sort du dû) |
| `cancellation` (vente annulée) | - reste de la créance |

Ordre : date de l'opération, instant d'enregistrement, puis vente → acompte → versements →
perte ou annulation. Le reste dû final = somme des restes des créances En cours.
"""

from dataclasses import dataclass, field, replace
from datetime import date, datetime

from app.domain.receivables.receivable import Receivable
from app.domain.receivables.values import ReceivableOrigin
from app.domain.shared.money import Money

ADDS = ("sale", "opening")
PAYS = ("deposit", "installment")
CLOSES = ("write_off", "cancellation")


@dataclass(frozen=True, slots=True, kw_only=True)
class StatementLine:
    kind: str
    on: date
    at: datetime
    receivable: Receivable
    amount: Money
    number: str | None = None
    cancelled: bool = False
    balance_after: Money = field(default_factory=Money.zero)


def _raw_lines(r: Receivable) -> list[tuple[int, StatementLine]]:
    def line(
        rank: int,
        kind: str,
        on: date,
        at: datetime,
        amount: Money,
        number: str | None = None,
        cancelled: bool = False,
    ) -> tuple[int, StatementLine]:
        entry = StatementLine(
            kind=kind,
            on=on,
            at=at,
            receivable=r,
            amount=amount,
            number=number,
            cancelled=cancelled,
        )
        return rank, entry

    out = []
    if r.origin is ReceivableOrigin.SALE:
        total = r.sale_total or r.initial_amount + r.paid_at_sale
        out.append(line(0, "sale", r.opened_on, r.recorded_at, total, r.sale_number))
        if r.paid_at_sale.amount > 0:
            out.append(
                line(1, "deposit", r.opened_on, r.recorded_at, r.paid_at_sale, r.sale_number)
            )
    else:
        out.append(line(0, "opening", r.opened_on, r.recorded_at, r.initial_amount))
    for item in r.installments:
        received, number = item.capture.received_at, str(item.number)
        out.append(
            line(2, "installment", item.paid_on, received, item.amount, number, not item.valid)
        )
    if r.write_off is not None:
        out.append(line(3, "write_off", r.write_off.on, r.write_off.at, Money.zero()))
    if r.sale_cancellation is not None:
        c = r.sale_cancellation
        out.append(line(3, "cancellation", c.on, c.at, Money.zero(), r.sale_number))
    return out


def statement_lines(receivables: list[Receivable]) -> list[StatementLine]:
    raw = [item for r in receivables for item in _raw_lines(r)]
    raw.sort(key=lambda pair: (pair[1].on, pair[1].at, pair[0], pair[1].number or ""))
    remaining: dict[object, Money] = {}
    closed: set[object] = set()
    balance, result = Money.zero(), []
    for _, line in raw:
        key, kind = line.receivable.id, line.kind
        rest = remaining.get(key, Money.zero())
        delta = Money.zero()
        if kind in ADDS:
            delta = line.amount
        elif kind in PAYS and not line.cancelled:
            delta = -line.amount
        if kind in CLOSES:
            effect = Money.zero() if key in closed else -rest
            line = replace(line, amount=rest)
            closed.add(key)
        else:
            effect = Money.zero() if key in closed else delta
        remaining[key] = rest + delta
        balance = balance + effect
        result.append(replace(line, balance_after=balance))
    return result
