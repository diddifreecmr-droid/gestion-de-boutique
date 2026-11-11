import type { Purchase } from "../../core/gateways/purchasingContract";
import { Badge } from "../../shared/ui";

/**
 * Statut d'un achat (UC-ACH-06), mot + icône (P7) : « À payer » en violet (argent qui reste dû,
 * design-system § 2.2), « Payé en partie » en orange, « Payé » en vert ; « Annulé » en rouge.
 */
export function PaymentBadge({ purchase }: { purchase: Purchase }) {
  if (purchase.status === "cancelled") return <Badge status="danger">Annulé</Badge>;
  switch (purchase.payment_status) {
    case "to_pay":
      return <Badge status="credit">À payer</Badge>;
    case "partially_paid":
      return <Badge status="warning">Payé en partie</Badge>;
    case "paid":
      return <Badge status="success">Payé</Badge>;
    default:
      throw new Error(`Statut de paiement inconnu : « ${purchase.payment_status} »`);
  }
}
