"""Lignes et frais d'un achat, et leur chiffrage (CDC § 20.3, RG-T10, H6, UC-ACH-01 étape 5).

- `PurchaseLine` : article, quantité **saisie** dans l'unité saisie, prix de l'unité saisie
  (≥ 0 ; 0 accepté pour un cadeau du fournisseur, question Q-35 remontée).
- `PurchaseFee` : Transport, Douane, Manutention ou Autre (« Autre » exige un libellé), montant
  ≥ 0. Les frais sont facultatifs.
- `CostedLine` : la ligne chiffrée — quantité de stock (RG-X02), total, part des frais,
  coût unitaire final par unité de stock — calculée par `cost_lines`, jamais saisie.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.audit.values import Scalar
from app.domain.catalog.ids import ArticleId
from app.domain.purchasing.costing import allocate_fees, final_unit_cost, line_total
from app.domain.purchasing.units import EntryUnit, entered_quantity
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.money import Money
from app.domain.shared.quantity import Quantity
from app.domain.shops.values import clean_optional

FEE_LABEL_MAX_LENGTH = 120


class FeeKind(StrEnum):
    TRANSPORT = "transport"
    CUSTOMS = "customs"  # Douane
    HANDLING = "handling"  # Manutention
    OTHER = "other"


@dataclass(frozen=True, slots=True, kw_only=True)
class PurchaseLine:
    article_id: ArticleId
    quantity: Decimal
    unit: EntryUnit
    unit_price: Money

    def __post_init__(self) -> None:
        if not isinstance(self.article_id, ArticleId):
            msg = "PurchaseLine.article_id doit être un ArticleId"
            raise TypeError(msg)
        object.__setattr__(self, "unit", EntryUnit(self.unit))
        object.__setattr__(self, "quantity", entered_quantity(self.quantity, self.unit))
        self.unit_price.require_non_negative("unit_price")

    def scalars(self, prefix: str) -> dict[str, Scalar]:
        return {
            f"{prefix}_article_id": str(self.article_id),
            f"{prefix}_quantity": str(self.quantity),
            f"{prefix}_unit": self.unit.value,
            f"{prefix}_unit_price": self.unit_price.amount,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class PurchaseFee:
    kind: FeeKind
    amount: Money
    label: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", FeeKind(self.kind))
        self.amount.require_non_negative("fees.amount")
        label = clean_optional(self.label, "fees.label", max_length=FEE_LABEL_MAX_LENGTH)
        if self.kind is FeeKind.OTHER and label is None:
            msg = "Les frais « Autre » exigent un libellé"
            raise ValidationFailed(msg, details={"field": "fees.label"})
        object.__setattr__(self, "label", label)

    def scalars(self, prefix: str) -> dict[str, Scalar]:
        return {
            f"{prefix}_kind": self.kind.value,
            f"{prefix}_label": self.label,
            f"{prefix}_amount": self.amount.amount,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class CostedLine:
    line: PurchaseLine
    stock_quantity: Quantity
    total: Money
    fee_share: Money
    unit_cost: Money
    """Coût unitaire final par unité de stock : porté par le mouvement « Entrée achat »."""


def cost_lines(
    lines: Sequence[PurchaseLine],
    stock_quantities: Sequence[Quantity],
    fees: Sequence[PurchaseFee],
) -> tuple[CostedLine, ...]:
    """Chiffre l'achat (RG-T10) : 20 x 520 000 + Douane 400 000 → coût unitaire 540 000."""
    if len(lines) != len(stock_quantities) or not lines:
        msg = "cost_lines : une quantité de stock par ligne, au moins une ligne"
        raise ValueError(msg)
    totals = [line_total(line.quantity, line.unit_price) for line in lines]
    shares = allocate_fees(totals, [fee.amount for fee in fees])
    return tuple(
        CostedLine(
            line=line,
            stock_quantity=quantity.require_positive("quantity"),
            total=total,
            fee_share=share,
            unit_cost=final_unit_cost(total, share, quantity.value),
        )
        for line, quantity, total, share in zip(
            lines, stock_quantities, totals, shares, strict=True
        )
    )
