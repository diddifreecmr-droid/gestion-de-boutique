/**
 * Unité saisie d'une ligne d'achat (CDC RG-X02, backend `domain/purchasing/units.py`) et
 * quantités tapées. Le serveur reste juge ; l'écran ne propose que les unités acceptées :
 *
 * | Article en | Unités proposées |
 * | --- | --- |
 * | Unité | Unité |
 * | Pièce | Pièce |
 * | Mètre | Mètre, Yard (1 yd = 0,9144 m) ; Pièce si l'article se vend à la pièce |
 *
 * Précision (RG-T08) : entière en Unité et Pièce, au dixième en Mètre et Yard.
 */
import type { EntryUnit } from "../../core/gateways/purchasingContract";
import { formatQuantity } from "../../shared/format";

export interface UnitArticle {
  stock_unit: string;
  sold_by_piece: boolean;
  piece_length_m: string | null;
}

export const UNIT_LABELS: Readonly<Record<EntryUnit, string>> = {
  UNIT: "Unité",
  PIECE: "Pièce",
  METER: "Mètre",
  YARD: "Yard",
};

/** Abréviation collée à une quantité (« 9,1 m », « 10 yd ») ; rien pour l'unité. */
const SHORT: Readonly<Record<EntryUnit, string | undefined>> = {
  UNIT: undefined,
  PIECE: "pièce(s)",
  METER: "m",
  YARD: "yd",
};

export function entryUnit(value: string): EntryUnit {
  if (value === "UNIT" || value === "PIECE" || value === "METER" || value === "YARD") return value;
  throw new Error(`Unité inconnue : « ${value} »`);
}

/** Unités proposées pour l'article (la première est l'unité de stock, présélectionnée). */
export function unitsFor(article: UnitArticle): EntryUnit[] {
  const stock = entryUnit(article.stock_unit);
  if (stock !== "METER") return [stock];
  const piece = article.sold_by_piece && article.piece_length_m !== null;
  return piece ? ["METER", "YARD", "PIECE"] : ["METER", "YARD"];
}

export function isTenths(unit: EntryUnit): boolean {
  return unit === "METER" || unit === "YARD";
}

/** « 9,1 m », « 4 » : une quantité et son unité. */
export function quantityWithUnit(value: string, unit: string): string {
  return formatQuantity(value, SHORT[entryUnit(unit)]);
}

export type TypedQuantity = { ok: true; value: string } | { ok: false; error: string };

const TYPED = /^\d+([.,]\d+)?$/;

/** Lit une quantité tapée (« 2,5 ») en chaîne décimale de l'API (« 2.5 »). */
export function parseEntryQuantity(text: string, unit: EntryUnit): TypedQuantity {
  const typed = text.trim().replace(/\s/g, "");
  if (typed === "") return { ok: false, error: "La quantité est vide" };
  if (!TYPED.test(typed)) return { ok: false, error: "Tapez un nombre, par exemple 2 ou 2,5" };
  const [whole = "", rawFraction = ""] = typed.replace(",", ".").split(".");
  const fraction = rawFraction.replace(/0+$/, "");
  if (!isTenths(unit) && fraction !== "") {
    return { ok: false, error: "Cette unité se compte en nombre entier" };
  }
  if (fraction.length > 1) return { ok: false, error: "Un chiffre après la virgule au plus" };
  const value = fraction === "" ? whole : `${whole}.${fraction}`;
  if (Number(value) === 0) return { ok: false, error: "La quantité doit être supérieure à zéro" };
  return { ok: true, value };
}

/** Valeur de l'API → texte du champ (« 2.5 » → « 2,5 »). */
export function quantityInput(value: string): string {
  const [whole = "", fraction = ""] = value.split(".");
  const trimmed = fraction.replace(/0+$/, "");
  return trimmed === "" ? whole : `${whole},${trimmed}`;
}
