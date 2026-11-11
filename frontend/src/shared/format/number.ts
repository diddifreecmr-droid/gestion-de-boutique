import { MINUS, THIN_NBSP } from "./characters";

/** Groupe les chiffres d'un entier positif écrit en base 10 : "1250000" → "1 250 000". */
export function groupThousands(digits: string): string {
  if (!/^\d+$/.test(digits)) {
    throw new Error(`groupThousands attend des chiffres seulement, reçu « ${digits} »`);
  }
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, THIN_NBSP);
}

/** Préfixe le signe moins typographique si `negative`. */
export function withSign(text: string, negative: boolean): string {
  return negative ? `${MINUS}${text}` : text;
}
