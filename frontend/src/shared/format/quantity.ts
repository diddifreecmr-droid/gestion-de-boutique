import { NBSP } from "./characters";
import { FormatError } from "./errors";
import { groupThousands, withSign } from "./number";

/** Nombre maximal de décimales affichées (ex. 2,375 m de tissu). */
export const MAX_QUANTITY_DECIMALS = 3;

const DECIMAL_STRING = /^-?\d+(\.\d+)?$/;

function toDecimalString(value: number | string): string {
  if (typeof value === "string") {
    if (!DECIMAL_STRING.test(value)) {
      throw new FormatError(`Quantité invalide : « ${value} »`);
    }
    return value;
  }
  if (!Number.isFinite(value) || Math.abs(value) > Number.MAX_SAFE_INTEGER) {
    throw new FormatError(`Quantité invalide : ${String(value)}`);
  }
  // Arrondi d'affichage seulement (corrige 0.1 + 0.2), la donnée n'est pas modifiée.
  return value.toFixed(MAX_QUANTITY_DECIMALS);
}

/**
 * Formate une quantité avec la virgule décimale : 2.5 → « 2,5 », 1250 → « 1 250 ».
 * Accepte un nombre ou une chaîne décimale (format des Decimal de l'API, « 2.500 »).
 * Les zéros de fin sont retirés. `unit` est collée par une espace insécable : « 2,5 m ».
 */
export function formatQuantity(value: number | string, unit?: string): string {
  const raw = toDecimalString(value);
  const negative = raw.startsWith("-");
  const [intPart = "", fracPart = ""] = raw.replace("-", "").split(".");
  if (fracPart.length > MAX_QUANTITY_DECIMALS && typeof value === "string") {
    throw new FormatError(
      `Quantité « ${value} » : ${String(MAX_QUANTITY_DECIMALS)} décimales au plus`,
    );
  }
  const fraction = fracPart.replace(/0+$/, "");
  const isZero = /^0*$/.test(intPart) && fraction === "";
  const body = groupThousands(intPart) + (fraction === "" ? "" : `,${fraction}`);
  const signed = withSign(body, negative && !isZero);
  return unit === undefined ? signed : `${signed}${NBSP}${unit}`;
}
