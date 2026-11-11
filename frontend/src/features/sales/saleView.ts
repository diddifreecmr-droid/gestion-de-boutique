/**
 * Ce que chaque rôle voit d'une vente (TR-05, RG-D02). Le serveur n'envoie les clés
 * `frozen_last_cost`, `frozen_wac`, `margin`, `margin_wac` qu'au propriétaire ; l'écran ne
 * les lit **que** par `ownerCosts`, qui refuse tout autre rôle. `null` = non calculable.
 */
import type { SaleReturn } from "../../core/gateways/returnsContract";
import type { SaleLineResult } from "../../core/gateways/salesContract";
import { formatMoney } from "../../shared/format";
import type { SaleRole } from "./salesNav";

export interface LineCosts {
  lastCost: number | null;
  wac: number | null;
  margin: number | null;
  marginWac: number | null;
}

export const NOT_COMPUTABLE = "non calculable";

/** Coûts figés et marges d'une ligne, pour le propriétaire ; `null` pour tout autre rôle. */
export function ownerCosts(role: SaleRole, line: SaleLineResult): LineCosts | null {
  if (role !== "owner") return null;
  if (!("frozen_last_cost" in line) || !("margin" in line)) {
    throw new Error(`Vente vue par le propriétaire sans coûts figés (${line.article_name})`);
  }
  return {
    lastCost: line.frozen_last_cost ?? null,
    wac: line.frozen_wac ?? null,
    margin: line.margin ?? null,
    marginWac: line.margin_wac ?? null,
  };
}

/**
 * Marge retirée par un retour, pour le propriétaire seulement ; `undefined` pour tout autre
 * rôle (le serveur ne l'envoie pas au vendeur). `null` = non calculable.
 */
export function ownerReturnMargin(role: SaleRole, made: SaleReturn): number | null | undefined {
  if (role !== "owner") return undefined;
  if (!("margin" in made)) throw new Error(`Retour vu par le propriétaire sans marge (${made.id})`);
  return made.margin ?? null;
}

export function moneyOrNot(amount: number | null): string {
  return amount === null ? NOT_COMPUTABLE : formatMoney(amount);
}
