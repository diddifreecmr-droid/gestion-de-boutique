import { formatMoney, NBSP } from "../format";
import { FOCUS_OUTLINE, PRESS_TRANSITION } from "./controlClasses";

/** Carte (§ 6.3) : surface, --radius-lg, padding --space-4, --shadow-card. */
export const CARD = "rounded-lg bg-surface p-4 shadow-card";

/** Carte ou ligne qui s'ouvre d'un appui : toute la surface est la cible. */
export const PRESSABLE = `w-full cursor-pointer text-left hover:bg-primary-soft ${PRESS_TRANSITION} ${FOCUS_OUTLINE}`;

const UNIT = `${NBSP}FCFA`;

/**
 * Sépare « 12 500 000 FCFA » en nombre et unité, pour afficher « FCFA » plus petit à la
 * suite d'un chiffre clé (§ 3.2). Le texte vient de formatMoney (fail-fast sur un non-entier).
 */
export function moneyParts(amount: number): { figure: string; unit: string } {
  const text = formatMoney(amount);
  if (!text.endsWith(UNIT)) {
    throw new Error(`moneyParts : « ${text} » ne se termine pas par l'unité FCFA`);
  }
  return { figure: text.slice(0, -UNIT.length), unit: "FCFA" };
}
