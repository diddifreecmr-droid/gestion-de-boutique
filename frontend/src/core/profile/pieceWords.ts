/**
 * Mot de la pièce servi par le profil (`piece_label`, décision du 2026-11-15) : « rouleau » en
 * Textile, « pièce » ailleurs. Les écrans n'écrivent jamais « pièce » en dur : ils déclinent ce
 * mot (« Au rouleau », « Prix du rouleau », « 7 rouleaux »). Un mot inconnu (genre et pluriel
 * inconnus) est une rupture de contrat : erreur explicite plutôt qu'une phrase fausse.
 */

export interface PieceWords {
  /** « rouleau » */
  one: string;
  /** « rouleaux » */
  many: string;
  /** « Rouleau » (titre, colonne) */
  title: string;
  /** « au rouleau » / « à la pièce » */
  per: string;
  /** « Au rouleau » / « À la pièce » (bascule de la vente) */
  perTitle: string;
  /** « du rouleau » / « de la pièce » */
  of: string;
  /** « Demi-rouleau » / « Demi-pièce » */
  half: string;
  /** « Rouleau complet » / « Pièce complète » */
  whole: string;
}

const KNOWN: Readonly<Record<string, PieceWords>> = {
  pièce: {
    one: "pièce",
    many: "pièces",
    title: "Pièce",
    per: "à la pièce",
    perTitle: "À la pièce",
    of: "de la pièce",
    half: "Demi-pièce",
    whole: "Pièce complète",
  },
  rouleau: {
    one: "rouleau",
    many: "rouleaux",
    title: "Rouleau",
    per: "au rouleau",
    perTitle: "Au rouleau",
    of: "du rouleau",
    half: "Demi-rouleau",
    whole: "Rouleau complet",
  },
};

export function pieceWords(label: string): PieceWords {
  const words = KNOWN[label.trim().toLocaleLowerCase("fr")];
  if (words === undefined) throw new Error(`Mot de la pièce inconnu : « ${label} »`);
  return words;
}

/** « 1 rouleau », « 7 rouleaux ». */
export function countText(count: number, words: PieceWords): string {
  if (!Number.isSafeInteger(count) || count < 0) {
    throw new Error(`Nombre de ${words.many} invalide : ${String(count)}`);
  }
  return `${String(count)} ${count > 1 ? words.many : words.one}`;
}
