import { groupThousands } from "../format/number";

/** 15 chiffres au plus : reste sous Number.MAX_SAFE_INTEGER (9 007 199 254 740 991). */
export const MAX_AMOUNT_DIGITS = 15;

/** Résultat de la lecture d'une saisie : un entier, `null` (champ vide) ou un refus. */
export type AmountParse = { ok: true; value: number | null } | { ok: false };

/** Garde seulement les chiffres et retire les zéros de tête (« 007 » → « 7 »). */
export function digitsOf(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  return digits.replace(/^0+(?=\d)/, "");
}

/**
 * Lit la saisie d'un montant FCFA (entier positif). Tout ce qui n'est pas un chiffre est
 * ignoré (séparateurs, lettres collées) ; au-delà de 15 chiffres la saisie est refusée.
 * Le résultat n'est jamais NaN.
 */
export function parseAmountInput(raw: string): AmountParse {
  const digits = digitsOf(raw);
  if (digits === "") return { ok: true, value: null };
  if (digits.length > MAX_AMOUNT_DIGITS) return { ok: false };
  return { ok: true, value: Number(digits) };
}

/** Texte affiché dans le champ : séparateur de milliers, sans unité (« 780 000 »). */
export function formatAmountInput(value: number | null): string {
  if (value === null) return "";
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new Error(`AmountField : valeur invalide ${String(value)} (entier positif attendu)`);
  }
  return groupThousands(String(value));
}

/** Nombre de chiffres situés avant la position `caret` dans `text`. */
export function digitsBefore(text: string, caret: number): number {
  return text.slice(0, caret).replace(/\D/g, "").length;
}

/** Position dans `text` juste après son `count`-ième chiffre (0 → début). */
export function caretAfterDigits(text: string, count: number): number {
  if (count <= 0) return 0;
  let seen = 0;
  for (let index = 0; index < text.length; index++) {
    if (/\d/.test(text.charAt(index))) seen++;
    if (seen === count) return index + 1;
  }
  return text.length;
}
