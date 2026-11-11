/**
 * Quantités du stock : chaînes décimales de l'API (`"2.500"`, specs § 6.1), affichées par
 * `shared/format` et saisies avec la virgule (« 2,5 »). Unités : `UNIT` et `PIECE` sont
 * entières (RG-T08 : 1,5 moto refusée), `METER` admet 3 décimales.
 */
import { formatQuantity, MAX_QUANTITY_DECIMALS } from "../../shared/format";

const UNITS = ["UNIT", "PIECE", "METER"] as const;
type StockUnit = (typeof UNITS)[number];

function stockUnit(unit: string): StockUnit {
  const known = UNITS.find((candidate) => candidate === unit);
  if (known === undefined) throw new Error(`Unité de stock inconnue : « ${unit} »`);
  return known;
}

export function isIntegral(unit: string): boolean {
  return stockUnit(unit) !== "METER";
}

/** « 2,5 m » pour le tissu, « 4 » pour une moto. */
export function quantityText(value: string, unit: string): string {
  return formatQuantity(value, stockUnit(unit) === "METER" ? "m" : undefined);
}

/** Écart ou mouvement signé : « +2 », « −1 » (le signe se lit sans la couleur, P7). */
export function signedQuantityText(value: string, unit: string): string {
  const text = quantityText(value, unit);
  return Number(value) > 0 ? `+${text}` : text;
}

export function isZero(value: string): boolean {
  return Number(value) === 0;
}

/** Valeur décimale de l'API → texte d'un champ (« 2.500 » → « 2,5 »). */
export function toInput(value: string | null): string {
  if (value === null) return "";
  const [whole = "", fraction = ""] = value.split(".");
  const trimmed = fraction.replace(/0+$/, "");
  return trimmed === "" ? whole : `${whole},${trimmed}`;
}

export type ParsedQuantity = { ok: true; value: string } | { ok: false; error: string };

const TYPED = /^\d+([.,]\d+)?$/;

/**
 * Lit une quantité saisie. `allowZero` : un comptage d'inventaire peut valoir 0, un
 * ajustement non. Renvoie la chaîne décimale envoyée à l'API (« 2.5 »).
 */
export function parseQuantity(text: string, unit: string, allowZero: boolean): ParsedQuantity {
  const typed = text.trim().replace(/\s/g, "");
  if (typed === "") return { ok: false, error: "La quantité est vide" };
  if (!TYPED.test(typed)) return { ok: false, error: "Tapez un nombre, par exemple 2 ou 2,5" };
  const value = typed.replace(",", ".");
  const [, fraction = ""] = value.split(".");
  if (isIntegral(unit) && fraction.replace(/0+$/, "") !== "") {
    return { ok: false, error: "Cet article se compte en nombre entier" };
  }
  if (fraction.length > MAX_QUANTITY_DECIMALS) {
    return {
      ok: false,
      error: `${String(MAX_QUANTITY_DECIMALS)} chiffres après la virgule au plus`,
    };
  }
  if (!allowZero && Number(value) === 0) {
    return { ok: false, error: "La quantité doit être supérieure à zéro" };
  }
  return { ok: true, value };
}

/** Indication sous un champ de quantité. */
export function quantityHint(unit: string): string | undefined {
  return isIntegral(unit) ? undefined : "En mètres, par exemple 2,5";
}
