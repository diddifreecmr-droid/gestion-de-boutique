import { NBSP } from "./characters";
import { FormatError } from "./errors";
import { groupThousands, withSign } from "./number";

/**
 * Formate un montant entier en FCFA : 1250000 → « 1 250 000 FCFA ».
 * Le FCFA n'a pas de subdivision : un montant non entier est une erreur de donnée,
 * on lève une FormatError plutôt que d'arrondir en silence.
 * Négatif (marge) : signe « − » (U+2212) devant le nombre.
 */
export function formatMoney(amount: number): string {
  if (!Number.isSafeInteger(amount)) {
    throw new FormatError(`Montant invalide : ${String(amount)} (entier FCFA attendu)`);
  }
  const negative = amount < 0;
  const digits = groupThousands(String(Math.abs(amount)));
  return `${withSign(digits, negative)}${NBSP}FCFA`;
}
