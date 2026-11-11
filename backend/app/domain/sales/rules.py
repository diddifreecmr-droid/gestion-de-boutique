"""Règles d'une vente partagées par l'agrégat (RG-T20, H20, Q-12, UC-VEN-07).

- Total = somme des totaux de ligne (aucune remise au Lot 1 : `gross_total` = `total`).
- **Comptant intégralement payé (Q-12 tranchée)** : la somme des paiements d'une vente au
  comptant est égale au total (`PAYMENT_INCOMPLETE` sinon ; le « montant remis » et la monnaie
  à rendre restent à l'écran, jamais envoyés). Un total de 0 se passe de paiement.
- Crédit : client obligatoire (H20, `CustomerRequired`), acompte de 0 au total exclu à la
  création (une vente « à crédit » entièrement payée est refusée : choisir « Comptant ») ; après
  une modification, le reste peut tomber à 0 (créance soldée, T17).
- Dans tous les cas, payé ≤ total (`OVERPAYMENT`, RG-T20, ERR-OVR-02/03).
- Modification : mêmes articles, modes et quantités, dans le même ordre (`LineChangeRefused`).
"""

from collections.abc import Sequence

from app.domain.sales.errors import (
    CustomerRequired,
    LineChangeRefused,
    PaymentIncomplete,
    SaleOverpayment,
)
from app.domain.sales.lines import SaleLine
from app.domain.sales.values import SaleContent, SaleKind
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.money import Money


def sale_total(lines: Sequence[SaleLine]) -> Money:
    return Money.total(line.line_total for line in lines)


def paid_of(content: SaleContent) -> Money:
    return Money.total(payment.amount for payment in content.payments)


def check_content(kind: SaleKind, content: SaleContent, *, creating: bool) -> None:
    total, paid = sale_total(content.lines), paid_of(content)
    if paid > total:
        raise SaleOverpayment(total=total, paid=paid)
    if kind is SaleKind.CASH and paid < total:
        raise PaymentIncomplete(total=total, paid=paid)
    if kind is SaleKind.CREDIT:
        if content.customer_id is None:
            raise CustomerRequired
        if creating and paid == total:
            msg = "Vente entièrement payée : choisissez « Comptant »"
            raise ValidationFailed(msg, details={"field": "kind"})


def check_same_lines(before: Sequence[SaleLine], after: Sequence[SaleLine]) -> None:
    if len(before) != len(after):
        raise LineChangeRefused("lines")
    for old, new in zip(before, after, strict=True):
        if old.article_id != new.article_id:
            raise LineChangeRefused("lines.article_id")
        if (old.sale_mode, old.quantity, old.stock_quantity) != (
            new.sale_mode,
            new.quantity,
            new.stock_quantity,
        ):
            raise LineChangeRefused("lines.quantity")
        if (old.frozen_last_cost, old.frozen_wac) != (new.frozen_last_cost, new.frozen_wac):
            msg = "Les coûts figés d'une vente ne changent jamais (RG-T13)"
            raise ValueError(msg)
