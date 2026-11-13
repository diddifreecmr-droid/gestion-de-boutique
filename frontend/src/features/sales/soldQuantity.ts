/**
 * Quantité d'une ligne vendue, à l'écran (fiche, confirmation) : « 2 », « 2,5 m », « 1 pièce ».
 * Le reçu, lui, imprime le `quantity_label` du serveur (« 1 pièce (5,49 m) », TEX-06) ;
 * `SaleLineResponse` ne le porte pas, d'où ce calcul à partir du mode et de la quantité.
 */
import { formatQuantity } from "../../shared/format";
import { piecesText } from "./textile";

export function soldQuantityText(line: { sale_mode: string; quantity: string }): string {
  switch (line.sale_mode) {
    case "unit":
      return formatQuantity(line.quantity);
    case "meter":
      return formatQuantity(line.quantity, "m");
    case "piece": {
      const count = Number(line.quantity);
      if (!Number.isSafeInteger(count)) throw new Error(`Pièces non entières : ${line.quantity}`);
      return piecesText(count);
    }
    default:
      throw new Error(`Mode de vente inconnu : « ${line.sale_mode} »`);
  }
}
