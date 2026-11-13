/**
 * Champs saisis sur une ligne de vente, selon les champs de vente du profil (`GET /profile`) :
 * détails par unité (Motos : couleur, châssis, moteur) ou taille et couleur de la ligne
 * (Prêt-à-porter, design-system § 7.4), avec leurs listes rapides. Aucune remise (QC-2).
 */

export interface LineFields {
  /** Une fiche par unité (n° de châssis : Motos). */
  units: boolean;
  /** Taille de la ligne (listes rapides). */
  size: boolean;
  /** Couleur de la ligne (listes rapides). */
  color: boolean;
}

/** Motos par défaut : c'est le profil d'origine de l'écran (détails par unité). */
export const UNIT_FIELDS: LineFields = { units: true, size: false, color: false };

export function lineFieldsOf(saleFields: readonly string[]): LineFields {
  const units = saleFields.includes("chassis_number");
  return {
    units,
    size: !units && saleFields.includes("size"),
    color: !units && saleFields.includes("color"),
  };
}

/** Panier « à la ligne » : un même article peut revenir dans une autre taille ou couleur. */
export const isBasket = (fields: LineFields) => fields.size || fields.color;

export const CLOTHING_SIZES = ["XS", "S", "M", "L", "XL", "XXL"] as const;
export const SHOE_SIZES = ["36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46"];
export const COMMON_COLORS = [
  "Noir",
  "Blanc",
  "Bleu",
  "Rouge",
  "Vert",
  "Jaune",
  "Rose",
  "Gris",
  "Beige",
  "Marron",
];

const SHOES = /chaussure|basket|sandale|escarpin|mocassin|botte|tennis|soulier|pointure/i;

/** Pointures 36–46 pour un article chaussant (d'après son nom), sinon tailles XS–XXL. */
export function sizeChoices(articleName: string): readonly string[] {
  return SHOES.test(articleName) ? SHOE_SIZES : CLOTHING_SIZES;
}

/** « T. M · Blanc » : résumé d'une ligne repliée (vide si rien n'est précisé). */
export function attributesText(line: { size: string; color: string }): string {
  const size = line.size.trim();
  const color = line.color.trim();
  return [size === "" ? null : `T. ${size}`, color === "" ? null : color]
    .filter((part): part is string => part !== null)
    .join(" · ");
}
