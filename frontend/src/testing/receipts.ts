/** Reçus d'exemple (vente, versement) pour les tests du PDF partagé. Réservé aux tests. */
import type { InstallmentReceipt } from "../core/gateways/receivablesContract";
import type { Receipt } from "../core/gateways/salesContract";

export function saleReceipt(overrides: Partial<Receipt> = {}): Receipt {
  return {
    title: "Reçu de vente",
    header: {
      shop_name: "Motos Garoua",
      city: "Garoua",
      phone: "+237690000001",
      address: "Marché central (près de la gare)",
      niu: "M0123456789",
      rccm: null,
      show_logo: false,
    },
    sale_id: "s1",
    number: "V-000130",
    provisional_number: null,
    sold_at: "2026-11-11T10:00:00Z",
    seller_name: "Issa Vendeur",
    customer: { name: "Moussa Abdou", phone: "+237690000000" },
    lines: [
      {
        article_name: "Haojue HJ125-8 édition spéciale « Sahel » très longue désignation",
        sale_mode: "unit",
        quantity: "1",
        quantity_label: "1",
        unit_price: 780_000,
        line_total: 780_000,
        details: [{ color: "Rouge", chassis_number: "LBX123", engine_number: null, size: null }],
      },
    ],
    total: 780_000,
    paid: 300_000,
    payments: [{ mode_name: "Espèces", amount: 300_000, reference: null }],
    remaining: 480_000,
    mentions: [{ code: "duplicate", label: "Duplicata" }],
    footer_message: "Merci de votre confiance",
    printing: {
      receipt_format: "58mm",
      paper_width_mm: 58,
      printable_width_mm: 48,
      padding_mm: 2,
      font_size_pt: 9,
      copies: 1,
    },
    print_sequence: 2,
    printed_at: "2026-11-11T10:00:00Z",
    ...overrides,
  };
}

export function installmentReceipt(
  overrides: Partial<InstallmentReceipt> = {},
): InstallmentReceipt {
  return {
    shop_name: "Motos Garoua",
    shop_city: "Garoua",
    shop_phone: "+237690000001",
    number: "R-000002",
    paid_on: "2026-11-11",
    customer_name: "Moussa Abdou",
    customer_phone: "+237690000000",
    amount: 480_000,
    mode_name: "MTN MoMo",
    reference: "MP-77",
    nature: "normal",
    cancelled: false,
    total_paid: 780_000,
    remaining: 0,
    settled: true,
    sale_number: "V-000130",
    ...overrides,
  };
}
