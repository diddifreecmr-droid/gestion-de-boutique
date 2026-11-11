"""Traduction des corps de requête des achats en saisies du cas d'utilisation (§ 6.1).

Identifiants : `EntityId.parse` (illisible → 400 `INVALID_IDENTIFIER`). `PATCH` : seuls les
champs présents ; `null` efface un champ facultatif (fournisseur, facture, note) mais est
refusé (400) pour les lignes, les frais, la date et le lieu.
"""

from typing import Any

from app.application.purchasing.resolver import FeeInput, LineInput, PurchaseInput
from app.domain.catalog.ids import ArticleId, AttachmentId
from app.domain.purchasing.ids import SupplierId
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import EntityId
from app.domain.shops.ids import LocationId
from app.interface.http.schemas.purchasing import (
    FeeRequest,
    LineRequest,
    PurchaseCreateRequest,
    PurchasePatch,
)

REQUIRED = frozenset({"lines", "fees", "purchase_date", "location_id"})
CONTROL = frozenset({"version", "reason", "confirm_price_gap"})
_PARSERS: dict[str, type[EntityId]] = {
    "location_id": LocationId,
    "supplier_id": SupplierId,
    "invoice_photo_id": AttachmentId,
}


def optional[IdT: EntityId](kind: type[IdT], text: str | None) -> IdT | None:
    return None if text is None else kind.parse(text)


def lines_of(lines: list[LineRequest]) -> tuple[LineInput, ...]:
    return tuple(
        LineInput(
            article_id=ArticleId.parse(line.article_id),
            quantity=line.quantity,
            unit_price=line.unit_price,
            unit=line.unit,
        )
        for line in lines
    )


def fees_of(fees: list[FeeRequest]) -> tuple[FeeInput, ...]:
    return tuple(FeeInput(kind=fee.kind, amount=fee.amount, label=fee.label) for fee in fees)


def input_of(body: PurchaseCreateRequest) -> PurchaseInput:
    return PurchaseInput(
        lines=lines_of(body.lines),
        fees=fees_of(body.fees),
        purchase_date=body.purchase_date,
        location_id=optional(LocationId, body.location_id),
        supplier_id=optional(SupplierId, body.supplier_id),
        invoice_ref=body.invoice_ref,
        invoice_photo_id=optional(AttachmentId, body.invoice_photo_id),
        note=body.note,
    )


def patch_of(body: PurchasePatch) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    for name in body.model_fields_set - CONTROL:
        value = getattr(body, name)
        if value is None and name in REQUIRED:
            msg = "Ce champ ne peut pas être vidé"
            raise ValidationFailed(msg, details={"field": name})
        if name == "lines":
            patch[name] = lines_of(value)
        elif name == "fees":
            patch[name] = fees_of(value)
        elif name in _PARSERS:
            patch[name] = optional(_PARSERS[name], value)
        else:
            patch[name] = value
    return patch
