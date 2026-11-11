/**
 * Caractères typographiques utilisés par tous les formats (design-system.md § 3.3).
 *
 * - THIN_NBSP (U+202F, espace fine insécable) sépare les milliers : « 1 250 000 ».
 *   C'est le séparateur de la norme française (et celui d'ICU pour fr-FR) ; il est
 *   insécable, donc un montant n'est jamais coupé en fin de ligne.
 * - NBSP (U+00A0, espace insécable) précède une unité (« FCFA », « m ») et entoure le
 *   « h » de l'heure : l'unité reste collée à son nombre.
 * - MINUS (U+2212) est le vrai signe moins, plus lisible que le trait d'union.
 */
export const THIN_NBSP = " ";
export const NBSP = " ";
export const MINUS = "−";
