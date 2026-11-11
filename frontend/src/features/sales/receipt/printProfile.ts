/**
 * Profil d'impression d'un reçu (specs § 9.1, design-system § 10). Source : le DTO de reçu
 * lui-même (`printing`, réglages de la boutique au moment de l'impression) — aucun appel en
 * plus. `receipt_format` désigne le profil : 58 mm → `thermal-58`, 80 mm → `thermal-80`
 * (défaut Motos), A5 / A4 → `a4-a5`. La largeur, la marge et la taille du texte réglées par la
 * boutique priment sur les valeurs par défaut du profil.
 */
import type { Receipt } from "../../../core/gateways/salesContract";

export type PrintProfileCode = "thermal-58" | "thermal-80" | "a4-a5";

const PROFILES: Readonly<Record<string, PrintProfileCode>> = {
  "58mm": "thermal-58",
  "80mm": "thermal-80",
  a5: "a4-a5",
  a4: "a4-a5",
};

export function printProfileOf(receiptFormat: string): PrintProfileCode {
  const profile = PROFILES[receiptFormat];
  if (profile === undefined) throw new Error(`Format de reçu inconnu : « ${receiptFormat} »`);
  return profile;
}

/** Marges de page du gabarit bureautique (design-system § 10 : 12 mm). */
const OFFICE_MARGIN_MM = 12;

/**
 * Règles `@page` et dimensions du reçu, propres à la boutique. Thermique : page de la largeur
 * du papier, hauteur libre (rouleau), sans marge d'imprimante ; la marge réglée est intérieure.
 */
export function pageRules(printing: Receipt["printing"]): string {
  const profile = printProfileOf(printing.receipt_format);
  const font = `font-size: ${String(printing.font_size_pt)}pt;`;
  if (profile === "a4-a5") {
    const size = printing.receipt_format === "a5" ? "A5" : "A4";
    return [
      `@page { size: ${size}; margin: ${String(OFFICE_MARGIN_MM)}mm; }`,
      `.receipt { ${font} }`,
    ].join("\n");
  }
  return [
    `@page { size: ${String(printing.paper_width_mm)}mm auto; margin: 0; }`,
    `.receipt { ${font} width: ${String(printing.printable_width_mm)}mm;` +
      ` padding: ${String(printing.padding_mm)}mm; }`,
  ].join("\n");
}
