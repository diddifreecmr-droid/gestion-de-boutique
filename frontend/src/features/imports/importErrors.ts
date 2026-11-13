/**
 * Message d'un téléchargement, d'un aperçu ou d'une confirmation d'import qui échoue (specs
 * § 6.2). `restart` : l'aperçu n'est plus utilisable, il faut déposer le fichier de nouveau.
 * Une erreur qui n'est ni de l'API ni réseau est un bug : relancée (fail-fast).
 */
import { ApiError, NetworkError } from "../../core/api/errors";
import { MODULE_DISABLED, MODULE_DISABLED_MESSAGE } from "../../core/profile/modules";

export interface ImportFailure {
  text: string;
  restart: boolean;
}

export const EXPIRED = "L'aperçu a expiré : déposez de nouveau le fichier.";
export const OFFLINE = "Connexion nécessaire : réessayez quand le réseau revient.";
export const NOTHING_VALID = "Aucune ligne à importer : corrigez le fichier.";
export const FORBIDDEN = "Vous n'avez pas le droit d'importer ce modèle.";
export const STORAGE_DOWN = "Stockage des fichiers indisponible : réessayez dans un instant.";
export const PREVIEW_UNKNOWN = "Aperçu introuvable : déposez de nouveau le fichier.";

const keep = (text: string): ImportFailure => ({ text, restart: false });

function reasonOf(error: ApiError): string {
  const reason = error.details["reason"];
  return typeof reason === "string" && reason !== "" ? reason : error.message;
}

export function importFailure(error: unknown): ImportFailure {
  if (error instanceof NetworkError) return keep(OFFLINE);
  if (!(error instanceof ApiError)) throw error;
  switch (error.code) {
    case "IMPORT_PREVIEW_EXPIRED":
      return { text: EXPIRED, restart: true };
    case "IMPORT_FILE_INVALID":
      return keep(`Ce fichier ne se lit pas : ${reasonOf(error)}.`);
    case "IMPORT_TOO_MANY_ROWS":
      return keep(`${error.message}. Coupez le fichier en plusieurs.`);
    case "VALIDATION_ERROR":
      return { text: NOTHING_VALID, restart: true };
    case MODULE_DISABLED:
      return keep(MODULE_DISABLED_MESSAGE);
    case "FORBIDDEN":
      return keep(FORBIDDEN);
    case "NOT_FOUND":
      return { text: PREVIEW_UNKNOWN, restart: true };
    case "STORAGE_UNAVAILABLE":
      return keep(STORAGE_DOWN);
    default:
      return keep(`L'import n'a pas abouti : ${error.message} (${error.code}).`);
  }
}
