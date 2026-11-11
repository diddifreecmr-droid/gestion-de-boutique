/**
 * Téléphone camerounais : 9 chiffres (6 ou 2 en tête), avec ou sans l'indicatif 237.
 * Renvoie la forme E.164 « +237690000000 », ou null si la saisie n'en est pas un.
 */
export function normalizePhone(raw: string): string | null {
  let digits = raw.replace(/\D/g, "");
  if (digits.length === 12 && digits.startsWith("237")) digits = digits.slice(3);
  if (!/^[26]\d{8}$/.test(digits)) return null;
  return `+237${digits}`;
}

export const PHONE_HINT = "9 chiffres, ex. 6 90 00 00 00";
