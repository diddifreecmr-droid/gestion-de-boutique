/**
 * Message affiché quand l'envoi d'une vente échoue (specs § 6.2). Une erreur qui n'est ni
 * une réponse de l'API ni une coupure réseau est un bug : elle est relancée (fail-fast).
 */
import { ApiError, NetworkError } from "../../core/api/errors";
import { duplicate, stockInsufficient } from "../../core/gateways/saleErrors";
import { formatQuantity } from "../../shared/format";
import type { LineDraft } from "./draft";

export const OFFLINE_MESSAGE =
  "Connexion nécessaire : la vente n'est pas enregistrée. Votre saisie est conservée ; " +
  "appuyez de nouveau sur « Valider la vente » quand le réseau revient.";

function stockMessage(error: ApiError, lines: readonly LineDraft[], locationName: string): string {
  const details = stockInsufficient(error);
  const name =
    lines.find((line) => line.article.id === details.article_id)?.article.name ?? "cet article";
  const here = `Stock insuffisant pour ${name} : ${formatQuantity(details.available)} disponible à ${locationName}.`;
  if (details.other_locations.length === 0) return `${here} Aucun stock dans les autres lieux.`;
  const others = details.other_locations
    .map((other) => `${other.location_name} : ${formatQuantity(other.available)}`)
    .join(", ");
  return `${here} Autres lieux — ${others}.`;
}

export function saleErrorMessage(
  error: unknown,
  lines: readonly LineDraft[],
  locationName: string,
): string {
  if (error instanceof NetworkError) return OFFLINE_MESSAGE;
  if (!(error instanceof ApiError)) throw error;
  switch (error.code) {
    case "STOCK_INSUFFICIENT":
      return stockMessage(error, lines, locationName);
    case "DUPLICATE": {
      const details = duplicate(error);
      const sale = details.sale_number === null ? "" : ` (vente ${details.sale_number})`;
      return `Le numéro de châssis ${details.value} a déjà été vendu${sale}.`;
    }
    case "CREDIT_LIMIT_EXCEEDED":
      return "Plafond de crédit dépassé pour ce client : seul le propriétaire peut valider cette vente.";
    case "OVERPAYMENT":
      return "Le total payé dépasse le montant de la vente.";
    case "FORBIDDEN":
      return "Vous n'avez pas le droit d'enregistrer cette vente.";
    default:
      return `La vente n'a pas été enregistrée : ${error.message} (${error.code}).`;
  }
}
