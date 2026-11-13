/**
 * Quantité et total d'une ligne selon son mode (unité, mètre, pièce : CDC § 19, QC-3). Le
 * serveur reste juge (`422 STOCK_INSUFFICIENT`) ; ces contrôles disent tout de suite quoi
 * corriger, en mètres (« 54,9 m »).
 */
import type { LineDraft } from "./draft";
import { meterStock } from "./draft";
import { metersText, meterTotal, parseLength, piecesTenths } from "./textile";

/** Total de la ligne : quantité × prix ; au mètre, longueur × prix au mètre arrondi au franc. */
export function lineTotal(line: LineDraft): number {
  const price = line.unitPrice ?? 0;
  if (line.mode !== "meter") return line.quantity * price;
  const length = parseLength(line.length);
  return length.ok ? meterTotal(length.tenths, price) : 0;
}

/** Longueur saisie (au mètre), `null` si elle n'est pas lisible. */
export function lineTenths(line: LineDraft): number | null {
  if (line.mode !== "meter") return null;
  const length = parseLength(line.length);
  return length.ok ? length.tenths : null;
}

/** Stock retiré par la ligne, en dixièmes de mètre (mètre ou pièce) ; `null` à l'unité. */
export function removedTenths(line: LineDraft): number | null {
  if (line.mode === "meter") return lineTenths(line);
  if (line.mode !== "piece") return null;
  const piece = line.article.piece;
  if (piece === undefined) throw new Error(`« ${line.article.name} » ne se vend pas à la pièce`);
  return piecesTenths(line.quantity, piece.length_m);
}

/** Erreur de quantité d'une ligne Textile : longueur illisible, ou plus que le stock du lieu. */
export function quantityIssue(line: LineDraft): string | undefined {
  if (line.mode === "unit") return undefined;
  if (line.mode === "meter") {
    const length = parseLength(line.length);
    if (!length.ok) return length.error;
  }
  const removed = removedTenths(line);
  const stock = meterStock(line.article);
  if (removed === null || removed <= stock) return undefined;
  return `Stock insuffisant : il reste ${metersText(stock)}, ${metersText(removed)} demandés`;
}
