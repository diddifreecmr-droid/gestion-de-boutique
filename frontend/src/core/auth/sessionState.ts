/** États de la session côté client (specs § 7.2) et messages de fin de session. */
import { ApiError } from "../api/errors";
import type { Me } from "./me";

export type SessionState =
  /** Au chargement : tentative silencieuse de rafraîchissement (cookie de l'appareil). */
  | { status: "restoring" }
  | { status: "signedOut"; notice: string | null }
  | { status: "signedIn"; me: Me }
  /** Restauration impossible (réseau, serveur) : l'écran propose « Réessayer ». */
  | { status: "failed"; error: Error };

/** Appel authentifié alors que la session est terminée : l'écran de connexion s'affiche. */
export class SessionEndedError extends Error {
  constructor(message = "Session terminée : reconnectez-vous") {
    super(message);
    this.name = "SessionEndedError";
  }
}

export const SESSION_EXPIRED_NOTICE = "Votre session a expiré : reconnectez-vous.";

/** Le serveur a refusé l'identité (jeton, cookie, compte) : la session doit se terminer. */
export function endsSession(error: unknown): error is ApiError {
  if (!(error instanceof ApiError)) return false;
  return error.status === 401 || error.code === "ACCOUNT_DISABLED";
}

/**
 * Message affiché sur l'écran de connexion. `restoring` : au chargement, l'absence de session
 * (`UNAUTHENTICATED`) est normale et ne mérite aucun message.
 */
export function endNotice(error: ApiError, restoring: boolean): string | null {
  if (error.code === "SESSION_REVOKED" || error.code === "ACCOUNT_DISABLED") return error.message;
  return restoring ? null : SESSION_EXPIRED_NOTICE;
}
