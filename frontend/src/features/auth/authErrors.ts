/** Traduction des erreurs de l'API en messages d'écran (CDC § 1.3 : message clair). */
import { DeviceIdError } from "../../core/api/device";
import { ApiError, NetworkError } from "../../core/api/errors";
import { SessionEndedError } from "../../core/auth/sessionState";
import { formatTime } from "../../shared/format";

export const NETWORK_MESSAGE =
  "Connexion nécessaire : vérifiez le réseau, votre saisie est gardée. Appuyez de nouveau pour renvoyer.";

/** Message du blocage (423) : « Compte bloqué jusqu'à 14 h 32 ». */
export function lockedMessage(error: ApiError): string {
  const until = error.details["until"];
  if (typeof until !== "string") return error.message;
  return `Compte bloqué jusqu'à ${formatTime(until)} après plusieurs essais faux. Le propriétaire peut le débloquer.`;
}

export interface ScreenError<F extends string> {
  field?: F;
  message: string;
}

/**
 * Erreur commune aux écrans d'authentification, ou `null` si l'écran doit la traiter lui-même.
 * Une erreur imprévue (bogue) est relancée : elle ne devient jamais un message vague.
 */
export function commonAuthError(error: unknown): ScreenError<never> | null {
  if (error instanceof NetworkError) return { message: NETWORK_MESSAGE };
  if (error instanceof DeviceIdError) return { message: error.message };
  // Session close pendant l'envoi : la garde de route ramène à la connexion avec le motif.
  if (error instanceof SessionEndedError) return { message: error.message };
  if (!(error instanceof ApiError)) throw error;
  if (error.code === "ACCOUNT_LOCKED") return { message: lockedMessage(error) };
  if (error.code === "ACCOUNT_DISABLED") return { message: error.message };
  return null;
}

/** Repli pour une erreur d'API sans traitement dédié : message du serveur et son code. */
export function fallbackMessage(error: unknown): string {
  if (error instanceof ApiError) return `${error.message} (code ${error.code})`;
  throw error;
}

export function validationField(error: unknown): string | null {
  if (!(error instanceof ApiError) || error.code !== "VALIDATION_ERROR") return null;
  const field = error.details["field"];
  return typeof field === "string" ? field : null;
}
