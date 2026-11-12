/**
 * Message d'un envoi ou d'une ouverture de pièce jointe qui échoue (specs § 6.2, § 9). Une
 * erreur qui n'est ni de l'API, ni réseau, ni un fichier refusé est un bug : relancée.
 */
import { ApiError, NetworkError } from "../../core/api/errors";
import { FileRejected } from "./prepareFile";

export const STORAGE_DOWN =
  "Stockage des fichiers indisponible : la photo est gardée, réessayez dans un instant.";
export const OFFLINE =
  "Connexion nécessaire : la photo est gardée, réessayez quand le réseau revient.";

export function attachmentErrorMessage(error: unknown): string {
  if (error instanceof FileRejected) return error.message;
  if (error instanceof NetworkError) return OFFLINE;
  if (!(error instanceof ApiError)) throw error;
  switch (error.code) {
    case "STORAGE_UNAVAILABLE":
      return STORAGE_DOWN;
    case "VALIDATION_ERROR":
      return "Fichier refusé : photo JPG ou PNG, ou PDF, 5 Mo au plus.";
    case "FORBIDDEN":
      return "Vous n'avez pas le droit de voir ou d'ajouter cette pièce.";
    case "NOT_FOUND":
      return "Pièce introuvable, ou réservée au propriétaire et au vendeur responsable.";
    default:
      return `L'envoi n'a pas abouti : ${error.message} (${error.code}).`;
  }
}
