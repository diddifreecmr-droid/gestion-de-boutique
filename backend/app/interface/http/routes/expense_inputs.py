"""Traduction des corps de requête des dépenses en saisies du cas d'utilisation (§ 6.1).

- Identifiants : `EntityId.parse` (illisible → 400 `INVALID_IDENTIFIER`).
- `X-Captured-At` : instant ISO 8601 **avec fuseau** ; sans fuseau → 400 (on ne devine jamais).
- `PATCH` : seuls les champs présents ; `null` efface un champ facultatif (description, lieu,
  bénéficiaire, justificatif) mais est refusé (400) pour un champ obligatoire.
"""

from datetime import datetime
from typing import Any

from app.application.expenses.references import ExpenseInput
from app.domain.expenses.ids import AttachmentId
from app.domain.shared.errors import ValidationFailed
from app.domain.shops.ids import ExpenseCategoryId, LocationId, PaymentModeId
from app.interface.http.schemas.expenses import ExpenseCreateRequest, ExpensePatch

REQUIRED = frozenset({"amount", "category_id", "spent_on", "payment_mode_id", "tags"})
_PARSERS: dict[str, Any] = {
    "category_id": ExpenseCategoryId.parse,
    "payment_mode_id": PaymentModeId.parse,
    "location_id": LocationId.parse,
    "attachment_id": AttachmentId.parse,
}


def captured_at_of(header: datetime | None) -> datetime | None:
    if header is not None and (header.tzinfo is None or header.utcoffset() is None):
        msg = "X-Captured-At doit indiquer son fuseau (ex. 2026-11-10T15:00:00+01:00)"
        raise ValidationFailed(msg, details={"field": "X-Captured-At"})
    return header


def _parsed(name: str, value: Any) -> Any:
    parser = _PARSERS.get(name)
    return value if value is None or parser is None else parser(value)


def input_of(body: ExpenseCreateRequest) -> ExpenseInput:
    return ExpenseInput(
        amount=body.amount,
        category_id=ExpenseCategoryId.parse(body.category_id),
        spent_on=body.spent_on,
        payment_mode_id=_parsed("payment_mode_id", body.payment_mode_id),
        tag_names=tuple(body.tags),
        description=body.description,
        location_id=_parsed("location_id", body.location_id),
        beneficiary=body.beneficiary,
        attachment_id=_parsed("attachment_id", body.attachment_id),
    )


def patch_of(body: ExpensePatch) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    for name in body.model_fields_set - {"version"}:
        value = getattr(body, name)
        if value is None and name in REQUIRED:
            msg = "Ce champ ne peut pas être vidé"
            raise ValidationFailed(msg, details={"field": name})
        if name == "tags":
            patch["tag_names"] = tuple(value)
        else:
            patch[name] = _parsed(name, value)
    return patch
