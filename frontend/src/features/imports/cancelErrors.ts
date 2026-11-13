/**
 * Message d'une annulation d'import refusée (UC-IMP-03, QC-6). `blocking` : opérations qui
 * s'appuient sur le lot ; `refresh` : l'état du lot a changé, il faut le relire.
 * Une erreur qui n'est ni de l'API ni réseau est un bug : relancée (fail-fast).
 */
import { ApiError, NetworkError } from "../../core/api/errors";
import type { ImportBatch } from "../../core/gateways/importsContract";
import { blockingTexts, dayMonth } from "./batchText";
import { OFFLINE } from "./importErrors";

export interface CancelFailure {
  text: string;
  blocking: string[];
  refresh: boolean;
}

export const BLOCKED = "Annulation impossible : ces opérations s'appuient sur le lot.";
export const ALREADY_CANCELLED = "Cet import est déjà annulé.";
export const OWNER_ONLY = "Seul le propriétaire peut annuler un import.";

const plain = (text: string, refresh = false): CancelFailure => ({ text, blocking: [], refresh });

export function cancelFailure(error: unknown, batch: ImportBatch): CancelFailure {
  if (error instanceof NetworkError) return plain(OFFLINE);
  if (!(error instanceof ApiError)) throw error;
  switch (error.code) {
    case "IMPORT_CANCEL_BLOCKED":
      return { text: BLOCKED, blocking: blockingTexts(error.details["blocking"]), refresh: false };
    case "IMPORT_CANCEL_TOO_LATE":
      return plain(
        `Délai dépassé : annulation possible jusqu'au ${dayMonth(batch.cancellable_until)}.`,
        true,
      );
    case "INVALID_STATE_TRANSITION":
      return plain(ALREADY_CANCELLED, true);
    case "FORBIDDEN":
      return plain(OWNER_ONLY);
    default:
      return plain(`L'annulation n'a pas abouti : ${error.message} (${error.code}).`);
  }
}
