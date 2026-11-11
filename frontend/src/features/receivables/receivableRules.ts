/** Règles d'affichage partagées par la liste, la fiche et le versement (CDC § 10). */
import type { Receivable } from "../../core/gateways/receivablesContract";

/** Origine en mots : « Vente V-000124 » ou la description d'une créance ancienne. */
export function originText(receivable: Receivable): string {
  if (receivable.sale_number !== null) return `Vente ${receivable.sale_number}`;
  return receivable.description ?? "Créance ancienne";
}

/** Une créance accepte un versement tant qu'il reste quelque chose (En perte : récupération). */
export function acceptsPayment(receivable: Receivable): boolean {
  return receivable.remaining > 0 && receivable.status !== "cancelled";
}

/**
 * Créances du client qui acceptent un versement, la plus ancienne d'abord (REC-03) : En cours
 * avant En perte (récupération), puis par date d'ouverture.
 */
export function debtsOf(items: readonly Receivable[], customerId: string): Receivable[] {
  const rank = (item: Receivable) => (item.status === "open" ? 0 : 1);
  return items
    .filter((item) => item.customer.id === customerId && acceptsPayment(item))
    .sort((a, b) => rank(a) - rank(b) || a.opened_on.localeCompare(b.opened_on));
}
