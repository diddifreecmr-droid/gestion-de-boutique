"""Lignes rendues d'un retour (UC-VEN-09 ; RG-T13, RG-T14, RG-M01 ; EXC-02).

- Une ligne rendue vise une ligne de la vente (`line`, position 1 = première), une quantité
  dans l'unité de vente (≤ vendue **non encore rendue**, sinon `RETURN_QUANTITY_EXCEEDED`) et un
  état de retour en stock (Vendable / Abîmé).
- **Montant et coût aux conditions de la vente d'origine** : montant = quantité x prix vendu,
  coût = quantité de stock x **coût figé** de la ligne (dernier coût et CMP), arrondis au franc
  (T04). Le dernier retour d'une ligne prend le **reste exact** (quantité de stock, montant,
  coûts) : la somme des retours égale la ligne, sans écart d'arrondi. Marge du retour =
  montant - coût (`None` si le coût est inconnu, RG-T15).
- Châssis rendus (motos) : à préciser parmi ceux de la ligne non encore rendus ; omis, ils
  valent « tous » quand la ligne est rendue entièrement. Ils sont ensuite libérés (RG-M01).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.domain.catalog.ids import ArticleId
from app.domain.sales.chassis import chassis_key
from app.domain.sales.errors import ReturnExceedsSold
from app.domain.sales.lines import SaleLine, SaleMode, round_franc
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.money import Money
from app.domain.shared.quantity import TENTH, Quantity, StockUnit
from app.domain.stock.values import StockCondition


@dataclass(frozen=True, slots=True, kw_only=True)
class ReturnedLine:
    line: int
    article_id: ArticleId
    article_name: str
    quantity: Decimal
    stock_quantity: Quantity
    condition: StockCondition
    amount: Money
    cost: Money | None = None
    cost_wac: Money | None = None
    chassis: tuple[str, ...] = ()
    """Clés normalisées des châssis rendus."""

    @property
    def margin(self) -> Money | None:
        return None if self.cost is None else self.amount - self.cost

    @property
    def margin_wac(self) -> Money | None:
        return None if self.cost_wac is None else self.amount - self.cost_wac


@dataclass(slots=True)
class AlreadyReturned:
    """Ce qui a déjà été rendu d'une ligne de vente (somme des retours précédents)."""

    quantity: Decimal = Decimal(0)
    stock: Decimal = Decimal(0)
    amount: Money = field(default_factory=Money.zero)
    cost: Money = field(default_factory=Money.zero)
    cost_wac: Money = field(default_factory=Money.zero)
    chassis: set[str] = field(default_factory=set)

    def add(self, line: ReturnedLine) -> None:
        self.quantity += line.quantity
        self.stock += line.stock_quantity.value
        self.amount += line.amount
        self.cost += line.cost or Money.zero()
        self.cost_wac += line.cost_wac or Money.zero()
        self.chassis.update(line.chassis)


def already_returned(lines: Sequence[ReturnedLine]) -> dict[int, AlreadyReturned]:
    found: dict[int, AlreadyReturned] = {}
    for line in lines:
        found.setdefault(line.line, AlreadyReturned()).add(line)
    return found


def _cost(stock: Decimal, unit_cost: Money | None) -> Money | None:
    return None if unit_cost is None else round_franc(stock * unit_cost.amount)


def _quantity(sold: SaleLine, wanted: Decimal | int | str) -> Decimal:
    grain = StockUnit.METER if sold.sale_mode is SaleMode.METER else StockUnit.UNIT
    return Quantity.of(wanted, grain).require_positive("lines.quantity").value


def _chassis(
    sold: SaleLine, done: AlreadyReturned, wanted: Sequence[str], *, full: bool
) -> tuple[str, ...]:
    available = [k for d in sold.details if (k := d.chassis_key) is not None]
    available = [key for key in available if key not in done.chassis]
    keys = tuple(dict.fromkeys(chassis_key(text) for text in wanted))
    if not keys:
        if available and not full:
            msg = "Précisez les numéros de châssis rendus"
            raise ValidationFailed(msg, details={"field": "lines.chassis"})
        return tuple(available)
    if len(keys) != len(wanted) or any(key not in available for key in keys):
        msg = "Châssis inconnu sur cette ligne, en double ou déjà rendu"
        raise ValidationFailed(msg, details={"field": "lines.chassis"})
    return keys


def returned_line(
    sold: SaleLine,
    position: int,
    wanted: Decimal | int | str,
    condition: StockCondition,
    done: AlreadyReturned,
    chassis: Sequence[str] = (),
) -> ReturnedLine:
    quantity = _quantity(sold, wanted)
    remaining = sold.quantity - done.quantity
    if quantity > remaining:
        raise ReturnExceedsSold(line=position, returnable=str(remaining))
    full = quantity == remaining
    unit = sold.stock_quantity.unit
    if full:
        stock = sold.stock_quantity.value - done.stock
        amount = sold.line_total - done.amount
        last = _cost(sold.stock_quantity.value, sold.frozen_last_cost)
        wac = _cost(sold.stock_quantity.value, sold.frozen_wac)
        cost = None if last is None else last - done.cost
        cost_wac = None if wac is None else wac - done.cost_wac
    else:
        share = sold.stock_quantity.value * quantity / sold.quantity
        step = TENTH if unit is StockUnit.METER else Decimal(1)
        stock = share.quantize(step, rounding=ROUND_HALF_UP)
        amount = round_franc(quantity * sold.unit_price.amount)
        cost = _cost(stock, sold.frozen_last_cost)
        cost_wac = _cost(stock, sold.frozen_wac)
    return ReturnedLine(
        line=position,
        article_id=sold.article_id,
        article_name=sold.article_name,
        quantity=quantity,
        stock_quantity=Quantity.of(stock, unit).require_positive("lines.quantity"),
        condition=StockCondition(condition),
        amount=amount,
        cost=cost,
        cost_wac=cost_wac,
        chassis=_chassis(sold, done, chassis, full=full),
    )
