"""Exécution d'une opération hors connexion par **le** cas d'utilisation en ligne (specs § 6.5).

- `sale.create` → `RecordSale` en mode **différé** (`deferred=True`, RG-T18 : stock négatif
  accepté, `stock_to_verify` + alerte) avec `sale_id = op_id` et le numéro provisoire gardé
  sur la vente (RG-T06, retrouvable par `GET /sales?q=`). Toutes les autres règles de la vente
  en ligne s'appliquent, dont le prix minimum du vendeur (UC-VEN-03 : refusée au serveur).
- `expense.create` → `RecordExpense` avec `expense_id = op_id` ; le numéro provisoire est
  gardé par la trace de synchronisation (`sync_operation`).
- `trip_step.create`, `trip_expense.create` : `AVAILABLE_IN_LOT_2` ; tout autre type :
  `OPERATION_NOT_ALLOWED_OFFLINE` (RG-T22).

Chaque cas d'utilisation ouvre et valide **sa propre** transaction (une opération = une
transaction) ; une erreur métier remonte telle quelle à l'appelant, qui la note `rejected`.
"""

from app.application.expenses.use_cases.record_expense import (
    RecordExpense,
    RecordExpenseCommand,
)
from app.application.sales.use_cases.record_sale import RecordSale, RecordSaleCommand
from app.application.security.actor import Actor
from app.application.sync.inputs import (
    LOT_2_TYPES,
    STOCK_TO_VERIFY,
    OperationDecoder,
    OperationInput,
    OperationNotice,
    OperationType,
    Outcome,
)
from app.domain.expenses.ids import ExpenseId
from app.domain.sales.ids import SaleId
from app.domain.shared.doc_number import DocType, ProvisionalDocNumber
from app.domain.shared.errors import InvalidIdentifier
from app.domain.shared.ids import DeviceId
from app.domain.sync.errors import (
    AvailableInLot2,
    OperationNotAllowedOffline,
    ProvisionalNumberInvalid,
)


def operation_type(raw: str) -> OperationType:
    """Type autorisé et disponible au Lot 1 ; sinon refus explicite (RG-T22)."""
    try:
        kind = OperationType(raw)
    except ValueError as exc:
        msg = "Cette saisie n'est pas possible hors connexion"
        raise OperationNotAllowedOffline(msg, details={"type": raw[:32]}) from exc
    if kind in LOT_2_TYPES:
        msg = "Saisie hors connexion des voyages disponible au Lot 2"
        raise AvailableInLot2(msg, details={"type": kind.value, "lot": 2})
    return kind


def provisional_number(
    text: str | None, doc_type: DocType, device: DeviceId
) -> ProvisionalDocNumber:
    """Numéro `<préfixe>-HL-<4 derniers hex de l'appareil>-<séquence>` de **cet** appareil."""
    if text is None:
        msg = "Numéro provisoire obligatoire pour une saisie hors connexion"
        raise ProvisionalNumberInvalid(msg, details={"field": "provisional_number"})
    try:
        number = ProvisionalDocNumber.parse(text)
    except InvalidIdentifier as exc:
        raise ProvisionalNumberInvalid(exc.message, details=exc.details) from exc
    expected = ProvisionalDocNumber.for_device(doc_type, device, number.sequence)
    if number != expected:
        msg = "Numéro provisoire d'un autre type de document ou d'un autre appareil"
        raise ProvisionalNumberInvalid(
            msg, details={"field": "provisional_number", "expected_prefix": str(expected)[:-5]}
        )
    return number


class OperationRunner:
    def __init__(self, record_sale: RecordSale, record_expense: RecordExpense) -> None:
        self._record_sale = record_sale
        self._record_expense = record_expense

    def run(self, actor: Actor, operation: OperationInput, decoder: OperationDecoder) -> Outcome:
        kind = operation_type(operation.type)
        if kind is OperationType.SALE_CREATE:
            return self._sale(actor, operation, decoder)
        if kind is OperationType.EXPENSE_CREATE:
            return self._expense(actor, operation, decoder)
        msg = f"Type d'opération sans exécutant : {kind.value}"  # garde : LOT_2_TYPES à jour
        raise RuntimeError(msg)

    def _sale(self, actor: Actor, operation: OperationInput, decoder: OperationDecoder) -> Outcome:
        number = provisional_number(operation.provisional_number, DocType.SALE, actor.device_id)
        command = RecordSaleCommand(
            data=decoder.sale(operation.op_id, operation.payload),
            sale_id=SaleId(operation.op_id.value),
            captured_at=operation.captured_at,
            deferred=True,
            provisional_number=number,
        )
        view, created = self._record_sale.execute(actor, command)
        warnings = tuple(OperationNotice(w.code, w.message, w.details) for w in view.warnings)
        if view.sale.stock_to_verify:
            warnings += (STOCK_TO_VERIFY,)
        return Outcome(
            entity_id=view.sale.id.value,
            number=str(view.sale.number),
            created=created,
            warnings=warnings,
        )

    def _expense(
        self, actor: Actor, operation: OperationInput, decoder: OperationDecoder
    ) -> Outcome:
        provisional_number(operation.provisional_number, DocType.EXPENSE, actor.device_id)
        command = RecordExpenseCommand(
            data=decoder.expense(operation.op_id, operation.payload),
            expense_id=ExpenseId(operation.op_id.value),
            captured_at=operation.captured_at,
        )
        view, created = self._record_expense.execute(actor, command)
        expense = view.expense
        return Outcome(entity_id=expense.id.value, number=str(expense.number), created=created)
