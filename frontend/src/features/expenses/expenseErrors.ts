/**
 * Message affiché quand une action des Dépenses échoue (specs § 6.2). Une erreur qui n'est
 * ni une réponse de l'API ni une coupure réseau est un bug : elle est relancée (fail-fast).
 */
import { ApiError, NetworkError } from "../../core/api/errors";
import { formatDate, formatTime } from "../../shared/format";

export const OFFLINE_MESSAGE =
  "Connexion nécessaire : rien n'est enregistré. Votre saisie est conservée ; réessayez quand le réseau revient.";

function deadlineText(error: ApiError): string {
  const deadline = error.details["deadline"];
  if (typeof deadline !== "string") {
    throw new Error("CORRECTION_WINDOW_CLOSED sans heure limite (details.deadline)");
  }
  return `${formatDate(deadline)} à ${formatTime(deadline)}`;
}

function dateText(error: ApiError): string {
  const min = error.details["min_date"];
  const max = error.details["max_date"];
  if (typeof max !== "string") return error.message;
  const from = typeof min === "string" ? `du ${formatDate(min)} ` : "";
  return `${error.message} : choisissez une date ${from}jusqu'au ${formatDate(max)}.`;
}

export function expenseErrorMessage(error: unknown): string {
  if (error instanceof NetworkError) return OFFLINE_MESSAGE;
  if (!(error instanceof ApiError)) throw error;
  switch (error.code) {
    case "CORRECTION_WINDOW_CLOSED":
      return `Délai dépassé (heure limite : ${deadlineText(error)}) : seul le propriétaire peut encore modifier cette dépense.`;
    case "BASE_CATEGORY_LOCKED":
      return "Une catégorie de base se renomme mais ne se désactive pas.";
    case "INACTIVE_REFERENCE":
      return "Élément désactivé entre-temps : choisissez-en un autre.";
    case "REASON_REQUIRED":
      return "Le motif est obligatoire.";
    case "DESCRIPTION_REQUIRED":
      return "Cette catégorie exige une description.";
    case "DATE_OUT_OF_RANGE":
      return dateText(error);
    case "VERSION_CONFLICT":
      return "Quelqu'un a modifié cet élément entre-temps : rechargez la fiche puis recommencez.";
    case "INVALID_TAG_MERGE":
      return "Fusion impossible : choisissez deux tags différents.";
    case "FORBIDDEN":
      return "Vous n'avez pas le droit de faire cette action.";
    default:
      return `L'action n'a pas abouti : ${error.message} (${error.code}).`;
  }
}
