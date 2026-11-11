/** Ventes de test : vue propriétaire, annulation, signalement, page de liste (tests seulement). */
import type {
  ErrorReport,
  RecordSaleCommand,
  SalePage,
  SaleResult,
} from "../core/gateways/salesContract";

export const NOW = "2026-11-11T10:00:00Z";
export const TODAY = "2026-11-11";

/**
 * Vue propriétaire : coûts figés et marges posés sur chaque ligne ; la 2ᵉ ligne et les
 * suivantes n'ont aucun coût connu (`null` = non calculable, RG-T15).
 */
export function withCosts(sale: SaleResult): SaleResult {
  return {
    ...sale,
    editable: sale.status === "valid",
    lines: sale.lines.map((line, index) =>
      index === 0
        ? {
            ...line,
            frozen_last_cost: 650_000,
            frozen_wac: 640_000,
            margin: line.line_total - 650_000 * Number(line.quantity),
            margin_wac: line.line_total - 640_000 * Number(line.quantity),
          }
        : { ...line, frozen_last_cost: null, frozen_wac: null, margin: null, margin_wac: null },
    ),
  };
}

export function cancelled(sale: SaleResult, reason: string): SaleResult {
  return {
    ...sale,
    status: "cancelled",
    editable: false,
    receivable: null,
    cancellation: { cancelled_at: NOW, cancelled_by: sale.seller_id, reason },
    version: sale.version + 1,
  };
}

export function report(sale: SaleResult, id: string, description: string): ErrorReport {
  return {
    id,
    sale_id: sale.id,
    sale_number: sale.number,
    description,
    status: "open",
    reported_by: sale.seller_id,
    reported_at: NOW,
    owner_reply: null,
    replied_at: null,
    version: 1,
  };
}

export function reported(sale: SaleResult, id: string, description: string) {
  const created = report(sale, id, description);
  return { sale: { ...sale, error_reports: [...sale.error_reports, created] }, report: created };
}

/**
 * Page de liste, plus récentes en haut. Totaux (Q-09) : ventes de la période − ventes annulées
 * pendant ; une vente du jour annulée le jour même compte donc pour 0.
 */
export function page(items: SaleResult[], overrides: Partial<SalePage> = {}): SalePage {
  const sign = (sale: SaleResult) => (sale.status === "cancelled" ? 0 : 1);
  return {
    items: [...items].reverse(),
    next_cursor: null,
    first_day: TODAY,
    last_day: TODAY,
    totals: {
      count: items.filter((sale) => sale.status === "valid").length,
      total: items.reduce((sum, sale) => sum + sign(sale) * sale.total, 0),
      paid: items.reduce((sum, sale) => sum + sign(sale) * sale.paid, 0),
    },
    ...overrides,
  };
}

/** Corps de vente de test (une Haojue HJ125-8 au comptant à Garoua), complété par `overrides`. */
export function saleCommand(overrides: Partial<RecordSaleCommand> = {}): RecordSaleCommand {
  return {
    id: `0193a7c2-0000-7000-8000-${String(Math.floor(Math.random() * 1e12)).padStart(12, "0")}`,
    location_id: "loc-garoua",
    sold_on: TODAY,
    kind: "cash",
    customer: null,
    lines: [
      {
        article_id: "art-hj125-8",
        sale_mode: "unit",
        quantity: "1",
        unit_price: 780_000,
        details: [{ color: "Rouge", chassis_number: "LBX0001", engine_number: null, size: null }],
      },
    ],
    payments: [{ mode_id: "pm-cash", amount: 780_000, reference: null }],
    credit: null,
    price_request_id: null,
    note: null,
    ...overrides,
  };
}
