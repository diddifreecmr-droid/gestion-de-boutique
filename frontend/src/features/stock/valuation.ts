/**
 * Valeur du stock (UC-STK-10, RG-T15) lue selon la méthode choisie : quantité × CMP (vue
 * principale) ou quantité × dernier coût (vue complémentaire). `amount: null` = « non
 * calculable » : au moins un article n'a pas de coût connu ; `known` est la part calculable.
 */
import type { Valuation } from "../../core/gateways/stockContract";
import { formatMoney } from "../../shared/format";
import { NOT_COMPUTABLE } from "../catalog/money";

export type Method = "wac" | "last_cost";

export const METHODS = [
  { value: "wac", label: "Au CMP" },
  { value: "last_cost", label: "Au dernier coût" },
] as const satisfies readonly { value: Method; label: string }[];

export interface Worth {
  amount: number | null;
  known: number;
  /** Articles sans coût connu. */
  missing: number;
}

export function worth(valuation: Valuation, method: Method): Worth {
  return method === "wac"
    ? { amount: valuation.at_wac, known: valuation.at_wac_known, missing: valuation.without_wac }
    : {
        amount: valuation.at_last_cost,
        known: valuation.at_last_cost_known,
        missing: valuation.without_last_cost,
      };
}

export function missingText(missing: number): string {
  return missing === 1
    ? "1 article sans coût connu"
    : `${String(missing)} articles sans coût connu`;
}

/** Ligne d'un lieu : montant, ou « non calculable » + part connue et articles sans coût. */
export function worthText(worth: Worth): string {
  if (worth.amount !== null) return formatMoney(worth.amount);
  return `${NOT_COMPUTABLE} (connu : ${formatMoney(worth.known)}, ${missingText(worth.missing)})`;
}
