/**
 * Message affiché quand une action des Réglages de la boutique échoue (specs § 6.2). Une
 * erreur qui n'est ni une réponse de l'API ni une coupure réseau est un bug : elle est
 * relancée (fail-fast).
 */
import { ApiError, NetworkError } from "../../core/api/errors";
import { MODULE_DISABLED, MODULE_DISABLED_MESSAGE } from "../../core/profile/modules";

export const OFFLINE_MESSAGE =
  "Connexion nécessaire : rien n'est enregistré. Réessayez quand le réseau revient.";

const MESSAGES: Readonly<Record<string, string>> = {
  DUPLICATE: "Ce nom ou ce numéro existe déjà dans la boutique.",
  LAST_ACTIVE_OWNER:
    "La boutique doit garder au moins un propriétaire actif : ajoutez-en un autre d'abord.",
  LAST_POINT_OF_SALE: "La boutique doit garder au moins un point de vente actif.",
  LOCATION_HAS_STOCK: "Ce lieu a encore du stock : videz-le avant de le désactiver.",
  LOCATION_IN_USE: "Ce lieu sert encore (vendeur, réglage) : changez-le d'abord.",
  LOCATION_NOT_POINT_OF_SALE: "Le lieu habituel d'un vendeur doit être un point de vente actif.",
  ROLE_NOT_IN_PROFILE: "Ce rôle n'existe pas pour ce type de boutique.",
  VERSION_CONFLICT:
    "Quelqu'un a modifié cet élément entre-temps : revenez au sommaire puis recommencez.",
  FORBIDDEN: "Vous n'avez pas le droit de faire cette action.",
  [MODULE_DISABLED]: MODULE_DISABLED_MESSAGE,
};

/** Champ nommé par `VALIDATION_ERROR` (`details.field`), s'il y en a un. */
function fieldOf(error: ApiError): string | null {
  const field = error.details["field"];
  return typeof field === "string" ? field : null;
}

export function settingsErrorMessage(error: unknown): string {
  if (error instanceof NetworkError) return OFFLINE_MESSAGE;
  if (!(error instanceof ApiError)) throw error;
  const known = MESSAGES[error.code];
  if (known !== undefined) return known;
  if (error.code === "VALIDATION_ERROR") {
    const field = fieldOf(error);
    return field === null
      ? `Saisie refusée : ${error.message}.`
      : `Saisie refusée (${field}) : ${error.message}.`;
  }
  return `L'action n'a pas abouti : ${error.message} (${error.code}).`;
}
