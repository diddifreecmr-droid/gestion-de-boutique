/**
 * Erreurs de `POST /auth/change-pin` (UC-SOC-07, décision du 11/11/2026) :
 * - 422 `CURRENT_PIN_INVALID` (`details.remaining_attempts`) : code actuel faux, session gardée ;
 * - 423 `PIN_CHANGE_LOCKED` (`details.until`) : changement bloqué, l'application reste utilisable ;
 * - 422 `PIN_TOO_SIMPLE` / `PASSWORD_TOO_WEAK` : nouveau secret refusé ;
 * - 400 `VALIDATION_ERROR` (`details.field`) : confirmation différente, nouveau = actuel.
 */
import { ApiError } from "../../core/api/errors";
import { formatTime } from "../../shared/format";
import { commonAuthError, fallbackMessage, validationField, type ScreenError } from "./authErrors";

export type ChangePinField = "current" | "next" | "confirmation";

const FIELD_BY_API: Readonly<Record<string, ChangePinField>> = {
  current_pin: "current",
  new_pin: "next",
  new_pin_confirmation: "confirmation",
};

export const PIN_TOO_SIMPLE_MESSAGE =
  "Code trop simple : évitez les suites (123456), les répétitions (000000) et votre numéro.";

function remainingText(error: ApiError): string {
  const remaining = error.details["remaining_attempts"];
  if (typeof remaining !== "number" || !Number.isSafeInteger(remaining)) return "";
  return ` — encore ${String(remaining)} essai${remaining > 1 ? "s" : ""}`;
}

function lockedText(error: ApiError): string {
  const until = error.details["until"];
  if (typeof until !== "string") return error.message;
  return `Changement de code bloqué jusqu'à ${formatTime(until)}. Vous pouvez continuer à utiliser l'application.`;
}

export function changePinError(
  error: unknown,
  kind: "pin" | "password",
): ScreenError<ChangePinField> {
  if (error instanceof ApiError) {
    if (error.code === "CURRENT_PIN_INVALID") {
      const what = kind === "pin" ? "Code actuel incorrect" : "Mot de passe actuel incorrect";
      return { field: "current", message: `${what}${remainingText(error)}` };
    }
    if (error.code === "PIN_CHANGE_LOCKED") return { message: lockedText(error) };
    if (error.code === "PIN_TOO_SIMPLE") return { field: "next", message: PIN_TOO_SIMPLE_MESSAGE };
    if (error.code === "PASSWORD_TOO_WEAK") return { field: "next", message: error.message };
    const field = FIELD_BY_API[validationField(error) ?? ""];
    if (field !== undefined) return { field, message: error.message };
  }
  return commonAuthError(error) ?? { message: fallbackMessage(error) };
}
