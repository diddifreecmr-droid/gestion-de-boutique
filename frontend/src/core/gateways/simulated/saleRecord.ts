/**
 * Vente et reçu simulés (vitrine `/_ui`) : mêmes formes que `SaleResponse` et que le DTO de
 * reçu. Aucun coût : la vue simulée est celle du vendeur (clés de coût absentes).
 */
import type { Receipt, RecordSaleCommand, SaleResult, SaleWarning } from "../salesContract";
import { LOCATIONS, PAYMENT_MODES } from "./seed";
import { locationOf, paymentsOf } from "./saleRules";
import { requireArticle, type World } from "./world";

interface Totals {
  number: string;
  total: number;
  paid: number;
  warnings: SaleWarning[];
  at: string;
}

export function saleOf(world: World, command: RecordSaleCommand, totals: Totals): SaleResult {
  const id = command.id ?? totals.number;
  const remaining = totals.total - totals.paid;
  const credit = command.kind === "credit";
  return {
    id,
    number: totals.number,
    provisional_number: null,
    status: "valid",
    kind: command.kind,
    sold_on: command.sold_on ?? totals.at.slice(0, 10),
    sold_at: totals.at,
    location_id: locationOf(command),
    seller_id: "vitrine",
    customer_id: command.customer?.id ?? null,
    total: totals.total,
    paid: totals.paid,
    remaining,
    // Comme le backend (T17) : la créance d'une vente porte l'identifiant de la vente.
    receivable: credit ? { id, remaining } : null,
    lines: command.lines.map((line) => {
      const article = requireArticle(world, line.article_id);
      return {
        article_id: article.id,
        article_name: article.name,
        sale_mode: line.sale_mode ?? "unit",
        quantity: line.quantity,
        stock_quantity: line.quantity,
        stock_unit: "UNIT",
        base_price: article.base_price,
        unit_price: line.unit_price,
        line_total: Number(line.quantity) * line.unit_price,
        details: (line.details ?? []).map((d) => ({
          color: d.color ?? null,
          chassis_number: d.chassis_number ?? null,
          engine_number: d.engine_number ?? null,
          size: d.size ?? null,
        })),
      };
    }),
    payments: paymentsOf(command).map((payment, index) => ({
      id: `${id}-p${String(index + 1)}`,
      mode_id: payment.mode_id,
      amount: payment.amount,
      reference: payment.reference ?? null,
      nature: credit ? "deposit" : "cash",
    })),
    credit: credit
      ? { reminder_on: command.credit?.reminder_on ?? null, terms: command.credit?.terms ?? null }
      : null,
    note: command.note ?? null,
    stock_to_verify: false,
    cancellation: null,
    created_by: "vitrine",
    device_id: "vitrine",
    captured_at: totals.at,
    received_at: totals.at,
    editable: false,
    version: 1,
    warnings: totals.warnings,
    error_reports: [],
  };
}

export function receiptOf(sale: SaleResult, sequence: number): Receipt {
  const modeName = (id: string) => PAYMENT_MODES.find((mode) => mode.id === id)?.name ?? id;
  const mentions = [
    ...(sale.kind === "credit" ? [{ code: "credit_sale", label: "Vente à crédit" }] : []),
    ...(sequence > 1 ? [{ code: "duplicate", label: "Duplicata" }] : []),
  ];
  const location = LOCATIONS.find((place) => place.id === sale.location_id);
  return {
    title: "Reçu de vente",
    header: {
      shop_name: "Motos Garoua (vitrine)",
      city: location?.name ?? "Garoua",
      phone: "+237690000001",
      address: null,
      niu: null,
      rccm: null,
      show_logo: false,
    },
    sale_id: sale.id,
    number: sale.number,
    provisional_number: null,
    sold_at: sale.sold_at,
    seller_name: "Vendeur de démonstration",
    customer: null,
    lines: sale.lines.map((line) => ({
      article_name: line.article_name,
      sale_mode: line.sale_mode,
      quantity: line.quantity,
      quantity_label: line.quantity, // vitrine Motos : ventes à l'unité seulement
      unit_price: line.unit_price,
      line_total: line.line_total,
      details: line.details,
    })),
    total: sale.total,
    paid: sale.paid,
    payments: sale.payments.map((p) => ({
      mode_name: modeName(p.mode_id),
      amount: p.amount,
      reference: p.reference,
    })),
    remaining: sale.remaining,
    mentions,
    footer_message: "Merci de votre confiance",
    printing: {
      receipt_format: "80mm",
      paper_width_mm: 80,
      printable_width_mm: 72,
      padding_mm: 3,
      font_size_pt: 10,
      copies: 1,
    },
    print_sequence: sequence,
    printed_at: new Date().toISOString(),
  };
}
