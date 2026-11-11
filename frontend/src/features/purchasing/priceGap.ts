/**
 * Avertissement « prix très différent du dernier coût » (UC-ACH-01, backend `price_gap.py`) :
 * le serveur refuse l'achat (`422 PRICE_GAP_CONFIRMATION_REQUIRED`) tant que l'utilisateur n'a
 * pas confirmé ; `details.lines` = `[{line, article_id, last_cost, unit_price}]` (`line` : rang
 * 0-based de la ligne). L'écran affiche « Le dernier achat était à 520 000 FCFA. Confirmer
 * 52 000 FCFA ? » puis renvoie la même saisie avec `confirm_price_gap: true`.
 */
import { ApiError } from "../../core/api/errors";
import { formatMoney } from "../../shared/format";

export const PRICE_GAP = "PRICE_GAP_CONFIRMATION_REQUIRED";

export interface PriceGap {
  line: number;
  lastCost: number;
  unitPrice: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function integer(item: Record<string, unknown>, key: string): number {
  const value = item[key];
  if (typeof value !== "number" || !Number.isSafeInteger(value)) {
    throw new Error(`${PRICE_GAP} : details.lines[].${key} illisible`);
  }
  return value;
}

/** Lignes en cause si `error` est l'avertissement d'écart de prix, sinon `null`. */
export function priceGapsOf(error: unknown): PriceGap[] | null {
  if (!(error instanceof ApiError) || error.code !== PRICE_GAP) return null;
  const lines = error.details["lines"];
  if (!Array.isArray(lines) || lines.length === 0) {
    throw new Error(`${PRICE_GAP} sans details.lines`);
  }
  return lines.map((item: unknown) => {
    if (!isRecord(item)) throw new Error(`${PRICE_GAP} : ligne illisible`);
    return {
      line: integer(item, "line"),
      lastCost: integer(item, "last_cost"),
      unitPrice: integer(item, "unit_price"),
    };
  });
}

/** « Le dernier achat était à 520 000 FCFA. Confirmer 52 000 FCFA ? » */
export function priceGapText(gap: PriceGap): string {
  return `Le dernier achat était à ${formatMoney(gap.lastCost)}. Confirmer ${formatMoney(gap.unitPrice)} ?`;
}
