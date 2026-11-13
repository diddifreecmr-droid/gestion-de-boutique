/**
 * Message affiché quand une action des Achats échoue (specs § 6.2, backend
 * `domain/purchasing/errors.py`). Une erreur qui n'est ni une réponse de l'API ni une coupure
 * réseau est un bug : elle est relancée (fail-fast). `PRICE_GAP_CONFIRMATION_REQUIRED` n'arrive
 * pas ici : la saisie le traite par une confirmation (`priceGap.ts`).
 */
import { ApiError, NetworkError } from "../../core/api/errors";
import { formatDate, formatMoney } from "../../shared/format";
import { OFFLINE_MESSAGE } from "../expenses/expenseErrors";
import { MODULE_DISABLED, MODULE_DISABLED_MESSAGE } from "../../core/profile/modules";

export { OFFLINE_MESSAGE };

export const STOCK_LEFT_MESSAGE =
  "Une partie de cette marchandise a déjà quitté le lieu de réception (vendue ou déplacée) : " +
  "la correction ou l'annulation est refusée. Passez par un ajustement de stock.";

function dateText(error: ApiError): string {
  const min = error.details["min_date"];
  const max = error.details["max_date"];
  if (typeof max !== "string") return error.message;
  const from = typeof min === "string" ? `du ${formatDate(min)} ` : "";
  return `${error.message} : choisissez une date ${from}jusqu'au ${formatDate(max)}.`;
}

function windowText(error: ApiError): string {
  const last = error.details["last_day"];
  if (typeof last !== "string") throw new Error("CORRECTION_WINDOW_CLOSED sans details.last_day");
  return `Délai dépassé : le comptable pouvait corriger cet achat jusqu'au ${formatDate(last)}. Demandez au propriétaire.`;
}

function overpaymentText(error: ApiError): string {
  const remaining = error.details["remaining"];
  if (typeof remaining !== "number") throw new Error("OVERPAYMENT sans details.remaining");
  return `Montant trop élevé : il dépasse le total de l'achat. Reste à payer : ${formatMoney(remaining)}.`;
}

function validationText(error: ApiError): string {
  const field = error.details["field"];
  if (field === "location_id") {
    return "Aucun lieu de réception par défaut n'est réglé : choisissez le lieu de réception.";
  }
  if (field === "fees") return "Des frais ne se répartissent pas sur des lignes à 0 FCFA.";
  return `${error.message}.`;
}

export function purchaseErrorMessage(error: unknown): string {
  if (error instanceof NetworkError) return OFFLINE_MESSAGE;
  if (!(error instanceof ApiError)) throw error;
  switch (error.code) {
    case "STOCK_ALREADY_LEFT":
      return STOCK_LEFT_MESSAGE;
    case "CORRECTION_WINDOW_CLOSED":
      return windowText(error);
    case "OVERPAYMENT":
      return overpaymentText(error);
    case "REASON_REQUIRED":
      return "Le motif est obligatoire.";
    case "VERSION_CONFLICT":
      return "Quelqu'un a modifié cet achat entre-temps : rechargez la fiche puis recommencez.";
    case "DUPLICATE":
      return "Un fournisseur porte déjà ce nom : choisissez-le dans la liste.";
    case "DATE_OUT_OF_RANGE":
      return dateText(error);
    case "VALIDATION_ERROR":
      return validationText(error);
    case "FORBIDDEN":
      return "Vous n'avez pas le droit de faire cette action.";
    case MODULE_DISABLED:
      return MODULE_DISABLED_MESSAGE;
    default:
      return `L'action n'a pas abouti : ${error.message} (${error.code}).`;
  }
}
