/**
 * Modes de paiement montrés d'emblée à la vente (audit UX du 13/11/2026) : « Espèces », choisi
 * par défaut, puis les 2 premiers autres modes actifs de la boutique ; le reste derrière
 * « Autre mode ». Sans mode « Espèces », les 3 premiers modes sont montrés et le premier choisi.
 */
import type { PaymentMode } from "../../core/gateways/catalogContract";

/** Nombre de modes montrés en plus d'« Espèces ». */
export const OTHER_VISIBLE_MODES = 2;

const CASH = "especes";

function fold(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .trim()
    .toLocaleLowerCase("fr");
}

export function isCash(mode: PaymentMode): boolean {
  return fold(mode.name) === CASH;
}

export interface ModeGroups {
  visible: PaymentMode[];
  hidden: PaymentMode[];
}

/** Modes visibles (Espèces d'abord) et modes derrière « Autre mode », ordre de la boutique gardé. */
export function groupModes(modes: readonly PaymentMode[]): ModeGroups {
  const cash = modes.find(isCash);
  const others = modes.filter((mode) => mode !== cash);
  const visible =
    cash === undefined
      ? others.slice(0, OTHER_VISIBLE_MODES + 1)
      : [cash, ...others.slice(0, OTHER_VISIBLE_MODES)];
  return { visible, hidden: others.filter((mode) => !visible.includes(mode)) };
}

/** Mode présélectionné : « Espèces », sinon le premier mode actif (jamais « À crédit »). */
export function defaultPayment(modes: readonly PaymentMode[]): string {
  const [first] = groupModes(modes).visible;
  if (first === undefined) throw new Error("La boutique n'a aucun mode de paiement actif");
  return first.id;
}
