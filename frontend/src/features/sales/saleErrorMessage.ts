/**
 * Message affiché quand l'envoi d'une vente échoue (specs § 6.2). Une erreur qui n'est ni
 * une réponse de l'API ni une coupure réseau est un bug : elle est relancée (fail-fast).
 */
import { ApiError, NetworkError } from "../../core/api/errors";
import { duplicate, paymentIncomplete, stockInsufficient } from "../../core/gateways/saleErrors";
import { formatMoney, formatQuantity } from "../../shared/format";
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

const remainingOf = (error: ApiError) => paymentIncomplete(error).remaining;

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
      if (details.sale_number === null) {
        return `Le numéro de châssis ${details.value} est saisi deux fois dans cette vente.`;
      }
      return `Le numéro de châssis ${details.value} a déjà été vendu (vente ${details.sale_number}).`;
    }
    case "CREDIT_LIMIT_EXCEEDED":
      return "Plafond de crédit dépassé pour ce client : seul le propriétaire peut valider cette vente.";
    case "OVERPAYMENT":
      return "Le total payé dépasse le montant de la vente.";
    case "PAYMENT_INCOMPLETE":
      return `Une vente au comptant est payée en entier : il manque ${formatMoney(remainingOf(error))}. Complétez les paiements ou choisissez « À crédit ».`;
    case "LOCATION_NOT_ALLOWED":
      return "Vous vendez depuis votre lieu de vente habituel : demandez au propriétaire de vous en attribuer un.";
    case "LOCATION_NOT_POINT_OF_SALE":
      return `${locationName} n'est plus un point de vente actif : rouvrez « Nouvelle vente » et choisissez un autre lieu.`;
    case "FORBIDDEN":
      return "Vous n'avez pas le droit d'enregistrer cette vente.";
    default:
      return `La vente n'a pas été enregistrée : ${error.message} (${error.code}).`;
  }
}

/**
 * Échec d'une action sur une vente existante (liste, annulation, signalement) : coupure
 * réseau ou refus du serveur dit en clair ; toute autre erreur est relancée (fail-fast).
 */
export function actionErrorMessage(error: unknown, action: string): string {
  if (error instanceof NetworkError)
    return `Connexion nécessaire : ${action} impossible pour l'instant. Réessayez quand le réseau revient.`;
  if (!(error instanceof ApiError)) throw error;
  if (error.code === "FORBIDDEN")
    return `Vous n'avez pas le droit de faire cette action (${action}).`;
  return `${action} refusé : ${error.message} (${error.code}).`;
}
