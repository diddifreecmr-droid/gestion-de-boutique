"""Créance liée à sa vente : révision, retour, annulation (UC-VEN-07, UC-VEN-08, UC-VEN-09).

Appelées par le handler `ReceivableSync` dans la transaction de la vente :

- `revise_from_sale` (`CreditSaleAmountsChanged`, MOD-01) : nouveau total, acompte, montant
  initial (480 000 → 460 000) et client. Refus `AMOUNT_BELOW_PAID` si le nouveau montant est
  inférieur au déjà versé : la modification de la vente est annulée en entier.
- `reduce_by_return` (`CreditSaleReturned`, T16b) : le montant initial baisse du montant
  retourné, **plafonné au reste réel** de la créance (T16b le calcule sur le reste de la
  vente, sans les versements) : jamais de reste négatif ; reste 0 → Soldée. L'excédent
  n'est **pas** un crédit client au Lot 1 (non conservé : à rembourser hors application).
- `cancel_by_sale` (`CreditSaleCancelled`, SCN-06) : la créance passe Annulée (hors total à
  recevoir) ; `refund_payments` → ses versements valides sont marqués « à rembourser ».
  Décision : admis depuis En cours, Soldée **ou** En perte (l'annulation de la vente prime,
  § 7.1 ne dessine que « En cours → Annulée ») ; une créance déjà annulée → 422.
"""

from datetime import date, datetime

from app.domain.receivables.errors import AmountBelowPaid
from app.domain.receivables.state import ReceivableState
from app.domain.receivables.values import ReceivableOrigin, SaleCancellation
from app.domain.sales.ids import CustomerId
from app.domain.shared.errors import InvalidAmount
from app.domain.shared.money import Money


class SaleLink(ReceivableState):
    def _require_sale_origin(self) -> None:
        if self.origin is not ReceivableOrigin.SALE:
            msg = "Seule une créance née d'une vente suit sa vente"
            raise ValueError(msg)

    def _set_initial(self, initial: Money) -> None:
        if initial < self.total_paid:
            raise AmountBelowPaid(initial=initial, paid=self.total_paid)
        self.initial_amount = initial

    def revise_from_sale(
        self, *, customer_id: CustomerId, total: Money, paid_at_sale: Money, initial: Money
    ) -> None:
        self._require_sale_origin()
        self.require_not_cancelled()
        if initial != total - paid_at_sale:
            msg = "Montant initial incohérent avec le total et l'acompte"
            raise ValueError(msg)
        self._set_initial(initial)
        self.customer_id = customer_id
        self.sale_total = total
        self.paid_at_sale = paid_at_sale

    def reduce_by_return(self, amount: Money) -> Money:
        """Baisse par un retour sur vente à crédit (`CreditSaleReturned`) ; renvoie la baisse
        appliquée (plafonnée au reste : l'excédent n'est pas un crédit client au Lot 1)."""
        self._require_sale_origin()
        self.require_not_cancelled()
        if amount.amount <= 0:
            msg = "Le montant d'un retour doit être supérieur à 0"
            raise InvalidAmount(msg, details={"field": "amount"})
        applied = min(amount, max(self.remaining, Money.zero()))
        self._set_initial(self.initial_amount - applied)
        return applied

    def cancel_by_sale(self, *, refund_payments: bool, on: date, at: datetime) -> None:
        self._require_sale_origin()
        self.require_not_cancelled()
        self.sale_cancellation = SaleCancellation(on, at)
        if refund_payments:
            self.installments = tuple(item.marked_to_refund() for item in self.installments)
