import type { Receipt } from "../../../core/gateways/salesContract";

/**
 * PROVISOIRE : le DTO du reçu de versement ne porte pas les réglages d'impression de la
 * boutique (le reçu de vente, si). Profil par défaut « Motos » : thermique 80 mm.
 */
export const DEFAULT_PRINTING: Receipt["printing"] = {
  receipt_format: "80mm",
  paper_width_mm: 80,
  printable_width_mm: 72,
  padding_mm: 2,
  font_size_pt: 11,
  copies: 1,
};
