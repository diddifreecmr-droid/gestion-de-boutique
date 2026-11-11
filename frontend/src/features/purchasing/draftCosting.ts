/** Chiffrage de la saisie en cours : lignes complètes passées à `costing.ts`. */
import { costPurchase, type CostInput, type Costing } from "./costing";
import type { PurchaseDraft } from "./draft";
import { parseEntryQuantity } from "./units";

/** « par unité », « par mètre » : le coût final est toujours par unité de stock (RG-X02). */
export function perStockUnit(stockUnit: string): string {
  if (stockUnit === "METER") return "par mètre";
  if (stockUnit === "PIECE") return "par pièce";
  return "par unité";
}

export interface Ready {
  name: string;
  stockUnit: string;
  input: CostInput;
}

/** Lignes complètes (article, quantité valide, prix) prêtes à chiffrer. */
function readyLines(draft: PurchaseDraft): Ready[] {
  return draft.lines.flatMap((line) => {
    if (line.article === null || line.unit === null || line.unitPrice === null) return [];
    const quantity = parseEntryQuantity(line.quantity, line.unit);
    if (!quantity.ok) return [];
    const { article } = line;
    return [
      {
        name: article.name,
        stockUnit: article.stock_unit,
        input: {
          quantity: quantity.value,
          unit: line.unit,
          unitPrice: line.unitPrice,
          stockUnit: article.stock_unit,
          pieceLengthM: article.piece_length_m,
        },
      },
    ];
  });
}

/** Chiffrage indicatif de la saisie (`costing.ts`), ou `null` sans aucune ligne complète. */
export function draftCosting(draft: PurchaseDraft): { costing: Costing; ready: Ready[] } | null {
  const ready = readyLines(draft);
  if (ready.length === 0) return null;
  const fees = draft.fees.flatMap((fee) => (fee.amount === null ? [] : [fee.amount]));
  return {
    costing: costPurchase(
      ready.map((line) => line.input),
      fees,
    ),
    ready,
  };
}
