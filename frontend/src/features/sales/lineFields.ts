/**
 * Champs saisis sur une ligne de vente, selon les champs de vente du profil (`GET /profile`) :
 * détails par unité (Motos : couleur, châssis, moteur), sinon rien. Prêt-à-porter simplifié
 * (décision du 2026-11-15, remplace les choix rapides taille/couleur de T40) : une vente est une
 * liste d'articles avec quantité et prix négocié. Aucune remise (QC-2).
 */

export interface LineFields {
  /** Une fiche par unité (n° de châssis : Motos). */
  units: boolean;
}

/** Motos par défaut : c'est le profil d'origine de l'écran (détails par unité). */
export const UNIT_FIELDS: LineFields = { units: true };

export function lineFieldsOf(saleFields: readonly string[]): LineFields {
  return { units: saleFields.includes("chassis_number") };
}
