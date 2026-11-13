/**
 * Vente Textile enregistrée par le faux serveur (tests seulement) : stock retiré au dixième
 * (QC-3), total au franc (demi vers le haut), aucun coût (vue de l'employé, TR-05).
 */
import type { RecordSaleCommand, SaleResult } from "../core/gateways/salesContract";
import { metersText, piecesTenths, tenthsValue, toTenths } from "../features/sales/textile";

type CommandLine = RecordSaleCommand["lines"][number];

export interface TextileArticle {
  id: string;
  name: string;
  /** Stock vendable à la Boutique, au dixième (« 54.9 »). */
  stock: string;
  /** Stock réel du serveur s'il diffère de l'affiché (vendu entre-temps ailleurs). */
  real?: string;
  piece_length_m: string | null;
  sold_by_piece: boolean;
  base_price: number;
  base_price_piece: number | null;
}

/** Dixièmes de mètre retirés du stock par la ligne. */
export function removedBy(article: TextileArticle, line: CommandLine): number {
  if (line.sale_mode === "meter") return toTenths(line.quantity);
  if (line.sale_mode !== "piece" || article.piece_length_m === null) {
    throw new Error(`Faux serveur Textile : mode « ${String(line.sale_mode)} » inattendu`);
  }
  return piecesTenths(Number(line.quantity), article.piece_length_m);
}

/** `quantity_label` du reçu (`domain/sales/quantity_label.py`). */
export function quantityLabel(article: TextileArticle, mode: string, quantity: string): string {
  if (mode === "meter") return metersText(toTenths(quantity));
  const length = (article.piece_length_m ?? "").replace(".", ",");
  return `${quantity} pièce${Number(quantity) > 1 ? "s" : ""} (${length} m)`;
}

export function saleResult(
  body: RecordSaleCommand,
  byId: ReadonlyMap<string, TextileArticle>,
  rank: number,
): SaleResult {
  const lines = body.lines.map((line) => {
    const article = byId.get(line.article_id);
    if (article === undefined) throw new Error("Faux serveur : article de la vente");
    const tenths = removedBy(article, line);
    const total =
      line.sale_mode === "meter"
        ? Math.floor((tenths * line.unit_price + 5) / 10)
        : Number(line.quantity) * line.unit_price;
    return {
      article_id: article.id,
      article_name: article.name,
      sale_mode: line.sale_mode ?? "meter",
      quantity: line.quantity,
      stock_quantity: tenthsValue(tenths),
      stock_unit: "METER",
      base_price: article.base_price,
      unit_price: line.unit_price,
      line_total: total,
      details: [],
    };
  });
  const total = lines.reduce((sum, line) => sum + line.line_total, 0);
  const at = "2026-11-13T10:00:00Z";
  const id = body.id ?? `sale-${String(rank)}`;
  return {
    id,
    number: `V-${String(rank).padStart(6, "0")}`,
    provisional_number: null,
    status: "valid",
    kind: body.kind ?? "cash",
    sold_on: body.sold_on ?? "2026-11-13",
    sold_at: at,
    location_id: body.location_id ?? "loc-boutique",
    seller_id: "seller",
    customer_id: null,
    total,
    paid: total,
    remaining: 0,
    receivable: null,
    lines,
    payments: (body.payments ?? []).map((payment, index) => ({
      id: `${id}-p${String(index)}`,
      mode_id: payment.mode_id,
      amount: payment.amount,
      reference: payment.reference ?? null,
      nature: "cash",
    })),
    credit: null,
    note: null,
    stock_to_verify: false,
    cancellation: null,
    created_by: "seller",
    device_id: "test",
    captured_at: at,
    received_at: at,
    editable: false,
    version: 1,
    warnings: [],
    error_reports: [],
  };
}
