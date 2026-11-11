/**
 * Avertissements acceptés par le serveur (propriétaire) : le plafond de crédit dépassé est
 * dit en chiffres (ERR-CRD-03) ; tout autre code garde le message du serveur.
 */
import type { SaleWarning } from "../../core/gateways/salesContract";
import { formatMoney } from "../../shared/format";

function amount(warning: SaleWarning, field: string): number {
  const value = warning.details[field];
  if (typeof value !== "number" || !Number.isSafeInteger(value)) {
    throw new Error(`Avertissement ${warning.code} : « ${field} » absent ou mal formé`);
  }
  return value;
}

export function warningText(warning: SaleWarning): string {
  if (warning.code !== "CREDIT_LIMIT_EXCEEDED") return warning.message;
  const limit = formatMoney(amount(warning, "limit"));
  const after = formatMoney(amount(warning, "due_after"));
  return `Plafond de crédit dépassé : ce client doit maintenant ${after} pour un plafond de ${limit}. Vente acceptée car vous êtes le propriétaire.`;
}
