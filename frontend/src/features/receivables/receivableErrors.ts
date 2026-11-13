/**
 * Message affiché quand une action des Créances échoue (specs § 6.2). Une erreur qui n'est
 * ni une réponse de l'API ni une coupure réseau est un bug : elle est relancée (fail-fast).
 */
import { ApiError, NetworkError } from "../../core/api/errors";
import { formatMoney } from "../../shared/format";
import { MODULE_DISABLED, MODULE_DISABLED_MESSAGE } from "../../core/profile/modules";

export const OFFLINE_MESSAGE =
  "Connexion nécessaire : rien n'est enregistré. Votre saisie est conservée ; réessayez quand le réseau revient.";

/** Reste à payer annoncé par `OVERPAYMENT` ; un détail mal formé rompt le contrat. */
export function overpaymentRemaining(error: ApiError): number {
  const remaining = error.details["remaining"];
  if (typeof remaining !== "number" || !Number.isSafeInteger(remaining)) {
    throw new Error(
      "Détails de l'erreur OVERPAYMENT invalides : « remaining » absent ou mal formé",
    );
  }
  return remaining;
}

export function receivableErrorMessage(error: unknown): string {
  if (error instanceof NetworkError) return OFFLINE_MESSAGE;
  if (!(error instanceof ApiError)) throw error;
  switch (error.code) {
    case "OVERPAYMENT":
      return `Le versement dépasse le reste à payer : il reste ${formatMoney(overpaymentRemaining(error))}.`;
    case "INVALID_STATE_TRANSITION":
      return `Action impossible dans l'état actuel : ${error.message}.`;
    case "REASON_REQUIRED":
      return "Le motif est obligatoire.";
    case "VERSION_CONFLICT":
      return "Quelqu'un a modifié cette créance entre-temps : rechargez la fiche puis recommencez.";
    case "INACTIVE_REFERENCE":
      return "Mode de paiement désactivé entre-temps : choisissez-en un autre.";
    case "DATE_OUT_OF_RANGE":
      return `${error.message} : choisissez une autre date.`;
    case "FORBIDDEN":
      return "Vous n'avez pas le droit de faire cette action.";
    case MODULE_DISABLED:
      return MODULE_DISABLED_MESSAGE;
    case "NOT_FOUND":
      return "Cette créance n'existe pas ou ne vous est pas confiée.";
    default:
      return `L'action n'a pas abouti : ${error.message} (${error.code}).`;
  }
}
