/** Textes des accueils : nombres en mots, éléments du Lot 2, comparaison sans pourcentage. */
import type {
  Compared,
  NotAvailable,
  PeriodOut,
  Valuation,
} from "../../core/gateways/reportingContract";
import { formatMoney } from "../../shared/format";
import { missingText, worth } from "../stock/valuation";
import { changePercent, previousWord } from "./periods";

/** « 1 vente », « 3 ventes », « Aucune vente » (`none`). */
export function count(value: number, one: string, many: string, none?: string): string {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new Error(`Nombre invalide : ${String(value)}`);
  }
  if (value === 0 && none !== undefined) return none;
  return `${String(value)} ${value === 1 ? one : many}`;
}

/** Élément d'un lot suivant (`{available: false, lot}`) : « Disponible au Lot 2 ». */
export function laterLot(block: NotAvailable): string {
  if (!Number.isSafeInteger(block.lot) || block.lot < 2) {
    throw new Error(`Bloc « non disponible » mal formé : ${JSON.stringify(block)}`);
  }
  return `Disponible au Lot ${String(block.lot)}`;
}

/** Variation pour `KpiCard` : un entier en %, ou la phrase qui dit pourquoi il n'y en a pas. */
export function comparison(
  value: Compared,
  period: PeriodOut,
): { change: number; reference: string } | { note: string } {
  const word = previousWord(period);
  const change = changePercent(value.change_pct);
  if (change === null) {
    return { note: `Pas de comparaison possible (${word} : ${formatMoney(value.previous)})` };
  }
  return { change, reference: `par rapport à ${word}` };
}

/** Valeur au CMP (§ 14.1) : montant, ou « non calculable » avec la part connue (RG-T15). */
export function valueRow(valuation: Valuation): { amount?: number; note: string } {
  const at = worth(valuation, "wac");
  if (at.amount !== null) return { amount: at.amount, note: "Au CMP" };
  return {
    note: `Non calculable : ${missingText(at.missing)} (connu : ${formatMoney(at.known)})`,
  };
}
