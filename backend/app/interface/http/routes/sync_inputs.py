"""Lecture des opérations de `POST /sync` : lot, puis `payload` validé **par opération**.

Le `payload` reprend le corps de `POST /sales` / `POST /expenses` et passe par les **mêmes**
modèles Pydantic et les mêmes traductions (`sale_input_of`, `input_of`) : une saisie hors
connexion obéit aux mêmes règles de forme qu'en ligne. Un payload invalide lève
`ValidationFailed` (`details.fields`, sans écho des valeurs) : seule cette opération est
refusée. Un `id` dans le payload doit valoir `op_id` (l'`op_id` est l'identifiant du document).
"""

from collections.abc import Mapping

from pydantic import BaseModel, ValidationError

from app.application.expenses.references import ExpenseInput
from app.application.sales.inputs import SaleInput
from app.application.sync.inputs import OperationInput, SyncBatch
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import DeviceId
from app.domain.sync.operation import SyncOperationId
from app.interface.http.routes.expense_inputs import input_of
from app.interface.http.routes.sales_inputs import sale_input_of
from app.interface.http.schemas.expenses import ExpenseCreateRequest
from app.interface.http.schemas.sales_requests import SaleCreateRequest
from app.interface.http.schemas.sync import SyncRequest


def _validated[M: BaseModel](model: type[M], payload: Mapping[str, object]) -> M:
    try:
        return model.model_validate(dict(payload))
    except ValidationError as exc:
        fields = [
            {
                "field": ".".join(str(part) for part in err["loc"]),
                "code": str(err["type"]),
                "message": str(err["msg"]),
            }
            for err in exc.errors()
        ]
        msg = "Saisie hors connexion invalide"
        raise ValidationFailed(msg, details={"fields": fields}) from exc


def _check_id(op_id: SyncOperationId, given: str | None) -> None:
    if given is not None and given.lower() != str(op_id):
        msg = "L'id du payload doit valoir op_id"
        raise ValidationFailed(msg, details={"field": "payload.id"})


class PayloadDecoder:
    """`OperationDecoder` de l'interface HTTP (sans état)."""

    def sale(self, op_id: SyncOperationId, payload: Mapping[str, object]) -> SaleInput:
        body = _validated(SaleCreateRequest, payload)
        _check_id(op_id, body.id)
        return sale_input_of(body)

    def expense(self, op_id: SyncOperationId, payload: Mapping[str, object]) -> ExpenseInput:
        body = _validated(ExpenseCreateRequest, payload)
        _check_id(op_id, body.id)
        return input_of(body)


def batch_of(body: SyncRequest) -> SyncBatch:
    return SyncBatch(
        device_id=DeviceId.parse(body.device_id),
        operations=tuple(
            OperationInput(
                op_id=SyncOperationId.parse(op.op_id),
                type=op.type,
                captured_at=op.captured_at,
                provisional_number=op.provisional_number,
                payload=op.payload,
            )
            for op in body.operations
        ),
    )
