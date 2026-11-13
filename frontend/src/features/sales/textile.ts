/**
 * Calculs de la vente Textile (CDC § 19, RG-X01, RG-X05, QC-3) sur des **entiers** : longueurs
 * en dixièmes de mètre (stock et saisie de vente au dixième), longueur de pièce en dix-millièmes
 * (6 yards = 5,4864 m). Mêmes règles que le serveur (`domain/profiles/textile.py`,
 * `domain/sales/lines.py`) : arrondi au dixième et au franc, demi vers le haut.
 */
import type { CatalogArticle, SaleShortcut } from "../../core/gateways/catalogContract";
import { formatQuantity } from "../../shared/format";

/** 1 yard = 0,9144 m : 6 yards en dix-millièmes de mètre (pièce sans longueur renseignée). */
const SIX_YARDS = 6 * 9144;
const DECIMAL = /^(\d+)(?:\.(\d+))?$/;

/** « 5.49 » → 54 900 dix-millièmes ; plus de 4 décimales significatives : rupture de contrat. */
function tenThousandths(value: string): number {
  const match = DECIMAL.exec(value);
  const fraction = (match?.[2] ?? "").replace(/0+$/, "");
  if (match?.[1] === undefined || fraction.length > 4) {
    throw new Error(`Longueur invalide : « ${value} »`);
  }
  return Number(match[1]) * 10_000 + Number(fraction.padEnd(4, "0"));
}

/** Dix-millièmes → dixièmes, demi vers le haut (5,49 → 5,5 ; 2,745 → 2,7). */
const roundTenth = (value: number) => Math.floor((value + 500) / 1000);

/** Stock ou longueur servis au dixième (« 54.900 » → 549) ; plus fin : rupture de contrat. */
export function toTenths(value: string): number {
  const exact = tenThousandths(value);
  if (exact % 1000 !== 0) throw new Error(`Quantité au mètre hors dixième : « ${value} »`);
  return exact / 1000;
}

/** Dixièmes → chaîne décimale envoyée à l'API (25 → « 2.5 »). */
export function tenthsValue(tenths: number): string {
  return `${String(Math.floor(tenths / 10))}.${String(tenths % 10)}`;
}

/** « 54,9 m », « 3 m » (virgule décimale, zéro inutile retiré). */
export function metersText(tenths: number): string {
  return formatQuantity(tenthsValue(tenths), "m");
}

/** « 5,49 m » : longueur d'une pièce telle que servie. */
export function lengthText(value: string): string {
  return formatQuantity(value, "m");
}

/** « 1 pièce », « 3 pièces ». */
export function piecesText(count: number): string {
  return `${String(count)} pièce${count > 1 ? "s" : ""}`;
}

/** Stock retiré par `pieces` pièces : longueur de la ligne arrondie au dixième (QC-3). */
export function piecesTenths(pieces: number, lengthM: string): number {
  return roundTenth(pieces * tenThousandths(lengthM));
}

/** Nombre de pièces entières dans `availableTenths` (stepper « À la pièce »). */
export function maxPieces(availableTenths: number, lengthM: string): number {
  let count = 0;
  while (piecesTenths(count + 1, lengthM) <= availableTenths) count += 1;
  return count;
}

/** « 54,9 m (≈ 9 pièces) » : stock toujours en mètres, pièces entières si la longueur est connue. */
export function stockText(availableTenths: number, pieceLengthM: string | undefined): string {
  const meters = metersText(availableTenths);
  if (pieceLengthM === undefined) return meters;
  return `${meters} (≈ ${piecesText(maxPieces(availableTenths, pieceLengthM))})`;
}

/** Total de ligne au mètre : longueur × prix au mètre, arrondi au franc (demi vers le haut). */
export function meterTotal(tenths: number, unitPrice: number): number {
  return Math.floor((tenths * unitPrice + 5) / 10);
}

export type ParsedLength = { ok: true; tenths: number } | { ok: false; error: string };

export const LENGTH_EMPTY = "Indiquez la longueur";
export const ONE_DECIMAL = "Une décimale au plus (ex. 2,5)";
const TYPED = /^\d+(?:[.,](\d+))?$/;

/** Longueur saisie au dixième, virgule ou point (« 2,5 ») ; « 2,55 » est refusé. */
export function parseLength(text: string): ParsedLength {
  const typed = text.trim().replace(/\s/g, "");
  if (typed === "") return { ok: false, error: LENGTH_EMPTY };
  const match = TYPED.exec(typed);
  if (match === null) return { ok: false, error: "Tapez une longueur, par exemple 2,5" };
  if ((match[1] ?? "").replace(/0+$/, "").length > 1) return { ok: false, error: ONE_DECIMAL };
  const tenths = toTenths(typed.replace(",", "."));
  if (tenths === 0) return { ok: false, error: "La longueur doit être supérieure à zéro" };
  return { ok: true, tenths };
}

/** Dixièmes → texte du champ (25 → « 2,5 »). */
export function lengthInput(tenths: number): string {
  return tenthsValue(tenths).replace(/\.0$/, "").replace(".", ",");
}

export type Resolved = { mode: "meter"; tenths: number } | { mode: "piece"; pieces: 1 };

/**
 * Raccourci appliqué à l'article (RG-X05, `resolve_shortcut` du serveur) : « Pièce complète »
 * passe « À la pièce » si l'article s'y vend, sinon la longueur de la pièce au mètre ;
 * « Demi-pièce » : la moitié, au dixième ; « 1 m »… : la longueur fixe.
 */
export function resolveShortcut(shortcut: SaleShortcut, article: CatalogArticle): Resolved {
  if (shortcut.basis === "length") {
    if (shortcut.length_m === null) throw new Error(`Raccourci « ${shortcut.code} » sans longueur`);
    return { mode: "meter", tenths: toTenths(shortcut.length_m) };
  }
  const piece =
    article.piece_length_m === undefined ? SIX_YARDS : tenThousandths(article.piece_length_m);
  if (shortcut.basis === "piece") {
    if (article.piece !== undefined) return { mode: "piece", pieces: 1 };
    return { mode: "meter", tenths: roundTenth(piece) };
  }
  if (shortcut.basis === "half_piece") return { mode: "meter", tenths: roundTenth(piece / 2) };
  throw new Error(`Raccourci de vente inconnu : « ${shortcut.basis} »`);
}

/** Libellé de la pastille : « Pièce complète (5,49 m) », « Demi-pièce (2,7 m) », « 1 m ». */
export function shortcutLabel(shortcut: SaleShortcut, article: CatalogArticle): string {
  if (shortcut.basis === "length") return shortcut.label;
  const resolved = resolveShortcut(shortcut, article);
  const length =
    resolved.mode === "piece"
      ? lengthText(article.piece?.length_m ?? "0")
      : metersText(resolved.tenths);
  return `${shortcut.label} (${length})`;
}
