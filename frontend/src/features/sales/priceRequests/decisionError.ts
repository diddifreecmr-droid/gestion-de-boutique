/** Refus d'une décision du propriétaire que l'écran explique (la liste est alors relue). */
import { ApiError } from "../../../core/api/errors";

export function decisionErrorMessage(error: unknown): string | null {
  if (!(error instanceof ApiError)) return null;
  if (error.code === "INVALID_STATE_TRANSITION") {
    const status = error.details["status"];
    if (status === "expired") return "Cette demande a expiré : le vendeur doit la refaire.";
    return "Cette demande n'est plus en attente : elle a déjà reçu une réponse.";
  }
  if (error.code === "VERSION_CONFLICT") {
    return "Cette demande a changé entre-temps : la liste est relue, vérifiez avant de décider.";
  }
  return null;
}
