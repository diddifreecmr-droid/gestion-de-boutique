"""UC-VEN-09 — Enregistrer un retour ou un échange (SCN-05, EXC-01, UC-PAP-01).

Droits (`exchange_rights.py`, QC-4) : retour = `SALE_RETURN` (propriétaire) ; échange =
`SALE_EXCHANGE` (propriétaire ; vendeur sur ses ventes si `employee_exchange_allowed`, dans le
délai `exchange_days` — le propriétaire le dépasse, journal sensible).

Dans **une** transaction, sur une vente valide (annulée → `INVALID_STATE_TRANSITION`) :
lignes rendues aux conditions de la vente (coûts figés, `returning.py`), motif obligatoire,
« Retour client » par ligne dans l'état choisi (Vendable / Abîmé), châssis rendus libérés,
retour au journal ; vente à crédit → `CreditSaleReturned` (baisse de la créance, T17).

- **Retour simple** : remboursement facultatif `{amount, mode_id, refunded_on}` borné par
  `sale_return.settlement` (`OVERPAYMENT`).
- **Échange** (`exchange`) : le retour d'abord (stock et châssis rendus disponibles), puis la
  nouvelle vente par **les règles de `RecordSale`** (lieu de la vente d'origine par défaut),
  au comptant ou **à crédit** (client de la vente d'origine imposé ; la différence non payée
  devient une créance par `CreditSaleRecorded`, `returning.exchange_sale_input`).
  La part de la valeur rendue non imputée sur la créance est un avoir : remboursée dans le
  mode `exchange.mode_id` et versée à la nouvelle vente dans ce même mode, plafonnée à son
  total ; le client ne paie (`sale.payments`) que la différence, ou la reçoit (avoir > total).
- Idempotent par `return_id` client (201 puis 200, rien n'est rejoué).
"""

from dataclasses import dataclass, replace

from app.application.ports.clock import Clock
from app.application.ports.uow import UnitOfWork, UnitOfWorkFactory
from app.application.sales import exchange_rights as rights
from app.application.sales import returning as rt
from app.application.sales.inputs import PaymentInput, SaleInput
from app.application.sales.ports import SaleRepository
from app.application.sales.retry import with_sale_retry
from app.application.sales.return_ports import SaleReturnRepository
from app.application.sales.return_views import SaleReturnView, return_view
from app.application.sales.use_cases.record_sale import RecordSale, RecordSaleCommand
from app.application.sales.views import SaleView
from app.application.security.access import Access
from app.application.security.actor import Actor
from app.application.security.policy import Policy
from app.application.shops.context import actor_shop, performer_of
from app.application.stock.ledger import StockLedger
from app.domain.sales.ids import SaleId, SaleReturnId
from app.domain.sales.lines import round_franc
from app.domain.sales.sale import Sale
from app.domain.sales.sale_return import Refund, SaleReturn, settlement
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity, StockUnit
from app.domain.shops.ids import PaymentModeId


@dataclass(frozen=True, slots=True, kw_only=True)
class ExchangeInput:
    sale: SaleInput
    mode_id: PaymentModeId
    """Mode dans lequel l'avoir est remboursé puis versé à la nouvelle vente."""
    sale_id: SaleId | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ReturnCommand:
    sale_id: SaleId
    lines: tuple[rt.ReturnLineInput, ...]
    reason: str
    refund: rt.RefundInput | None = None
    exchange: ExchangeInput | None = None
    return_id: SaleReturnId | None = None


def planned_total(data: SaleInput) -> Money:
    """Total de la nouvelle vente, calculé comme `SaleLine.line_total` (arrondi T04)."""
    return Money.total(
        round_franc(Quantity.of(item.quantity, StockUnit.METER).value * item.unit_price)
        for item in data.lines
    )


class RecordReturn:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        policy: Policy,
        ledger: StockLedger,
        clock: Clock,
        record: RecordSale,
    ) -> None:
        self._uow_factory = uow_factory
        self._policy = policy
        self._ledger = ledger
        self._clock = clock
        self._record = record

    def execute(self, actor: Actor, command: ReturnCommand) -> tuple[SaleReturnView, bool]:
        exchanging = command.exchange is not None
        access = rights.required_access(self._policy, actor, exchange=exchanging)  # avant lecture
        return with_sale_retry(lambda: self._attempt(actor, command, access))

    def _attempt(
        self, actor: Actor, command: ReturnCommand, access: Access
    ) -> tuple[SaleReturnView, bool]:
        with self._uow_factory(actor_shop(actor)) as uow:
            sale = SaleRepository.within(uow).get(command.sale_id)
            if command.exchange is not None:
                rights.require_own_exchange(uow, actor, access, sale)
            returns = SaleReturnRepository.within(uow)
            if command.return_id is not None:
                existing = returns.find(command.return_id)
                if existing is not None:
                    rights.require_same_sale(access, existing, sale)
                    return return_view(self._policy, actor, existing), False
            sale.require_valid()
            late = command.exchange is not None and rights.exchange_is_late(
                uow, access, sale, self._clock.today()
            )
            made, exchange = self._record_in(uow, actor, command, sale, late=late)
            uow.commit()
        return return_view(self._policy, actor, made, exchange), True

    def _record_in(
        self, uow: UnitOfWork, actor: Actor, command: ReturnCommand, sale: Sale, *, late: bool
    ) -> tuple[SaleReturn, SaleView | None]:
        now, today = self._clock.now(), self._clock.today()
        previous = SaleReturnRepository.within(uow).for_sale(sale.id)
        lines = rt.returned_lines(sale, command.lines, previous)
        exchange, new_id, refund = command.exchange, None, None
        if exchange is not None:
            new_id = exchange.sale_id or SaleId.new()
            value = Money.total(line.amount for line in lines)
            avoir = settlement(sale, value, previous).refund_max
            if avoir.amount > 0:
                mode = rt.active_mode(uow, exchange.mode_id)
                refund = Refund(amount=avoir, mode_id=mode, refunded_on=today)
        elif command.refund is not None:
            refund = rt.checked_refund(uow, sale, command.refund, today)
        made = SaleReturn.record(
            sale,
            lines,
            reason=command.reason,
            previous=previous,
            refund=refund,
            performer=performer_of(actor),
            now=now,
            exchange_sale_id=new_id,
            return_id=command.return_id,
            late=late,
        )
        SaleReturnRepository.within(uow).add(made)
        rt.post_entries(uow, self._ledger, sale, made)
        rt.release_returned(uow, made)
        if exchange is None or new_id is None:
            return made, None
        data = exchange.sale
        applied = min(made.refunded, planned_total(data))
        if applied.amount > 0:
            avoir_payment = PaymentInput(
                mode_id=exchange.mode_id,
                amount=applied.amount,
                reference=f"Échange {sale.number}",
            )
            data = replace(data, payments=(*data.payments, avoir_payment))
        data = rt.exchange_sale_input(sale, data)
        _, view = self._record.record_in(
            uow, actor, RecordSaleCommand(data=data, sale_id=new_id), now
        )
        return made, view
