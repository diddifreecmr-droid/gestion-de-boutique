/**
 * Avertissements d'une vente acceptée : plafond de crédit dépassé (propriétaire, ERR-CRD-03) et
 * prix sous le minimum (accord non exigé, décision client) dits en chiffres ; tout autre code
 * garde le message du serveur.
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
  if (warning.code === "PRICE_BELOW_MINIMUM") {
    return `Prix inférieur au minimum de ${formatMoney(amount(warning, "min_price"))} (ligne ${String(amount(warning, "line"))}). Vente enregistrée.`;
  }
  if (warning.code !== "CREDIT_LIMIT_EXCEEDED") return warning.message;
  const limit = formatMoney(amount(warning, "limit"));
  const after = formatMoney(amount(warning, "due_after"));
  return `Plafond de crédit dépassé : ce client doit maintenant ${after} pour un plafond de ${limit}. Vente acceptée car vous êtes le propriétaire.`;
}

/**
 * Avertissement sous le prix d'une ligne (design-system § 7.4, règle du Lot 1) : « Sous le prix
 * minimum (12 000 FCFA) : la vente sera notée au journal » ; accord exigé par le réglage : dit.
 */
export function belowMinimumText(minimum: number, approval: boolean): string {
  const head = `Sous le prix minimum (${formatMoney(minimum)})`;
  return approval
    ? `${head} : validation du propriétaire nécessaire.`
    : `${head} : la vente sera notée au journal`;
}
