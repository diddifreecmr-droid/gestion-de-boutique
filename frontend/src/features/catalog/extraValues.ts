/** Seuil d'alerte et notes : conversion et contrôle de la saisie. */
/** Seuil d'alerte : nombre positif, au dixième près (`alert_threshold`, specs § 6.3). */
const THRESHOLD = /^\d+([.,]\d)?$/;

export interface ExtraDraft {
  threshold: string;
  notes: string;
}

export function thresholdError(text: string): string | undefined {
  const value = text.trim();
  return value === "" || THRESHOLD.test(value)
    ? undefined
    : "Seuil d'alerte : nombre attendu (ex. 5)";
}

/** `null` = seuil de la boutique. */
export function thresholdValue(text: string): string | null {
  const value = text.trim();
  return value === "" ? null : value.replace(",", ".");
}

export function notesValue(text: string): string | null {
  const value = text.trim();
  return value === "" ? null : value;
}
