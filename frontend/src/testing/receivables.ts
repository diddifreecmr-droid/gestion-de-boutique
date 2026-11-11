/**
 * Faux serveur des Créances (tests seulement) : réponses typées par le contrat généré.
 * Jour de référence : 11/11/2026 à Douala.
 */
import type {
  CustomerSummary,
  Installment,
  Member,
  PaymentMode,
  Receivable,
  ReceivableList,
} from "../core/gateways/receivablesContract";
import { json, meBody, ROUTES, SHOP_A, tokenBody, type Reply } from "./fakeApi";

export const OWNER_ID = "01890a5d-ac96-774b-bcce-b302099a8000";
export const SELLER_ID = "01890a5d-ac96-774b-bcce-b302099a8002";
export const OTHER_SELLER_ID = "01890a5d-ac96-774b-bcce-b302099a8003";
export const CUSTOMER_ID = "cust-moussa";
export const RECEIVABLE_ID = "sale-124";
export const NOW = "2026-11-11T10:00:00Z";
export const TODAY = "2026-11-11";

export const API = `/api/v1/shops/${SHOP_A}`;
export const route = (method: string, path: string) => `${method} ${API}${path}`;
export const RECEIVABLES_PATH = `/s/${SHOP_A}/creances`;
export const DETAIL_PATH = `${RECEIVABLES_PATH}?vue=fiche&id=${RECEIVABLE_ID}`;
export const GET_ONE = route("GET", `/receivables/${RECEIVABLE_ID}`);
export const LIST = route("GET", "/receivables");
export const SEARCH = route("GET", "/customers?q=Moussa");

export const CUSTOMER: CustomerSummary = {
  id: "cust-moussa",
  name: "Moussa Hamadou",
  phone: "+237690000001",
  kind: "individual",
  city: null,
  address: null,
  id_doc_type: null,
  id_doc_number: null,
  id_doc_photo_id: null,
  credit_limit: null,
  note: null,
  created_by: "x",
  version: 1,
};

/** Charge à l'avance les écrans chargés à la demande (sous couverture, l'import est lent). */
export async function preloadReceivables(): Promise<void> {
  await Promise.all([
    import("../features/receivables/ReceivablesRoute"),
    import("../features/receivables/receipt/InstallmentReceiptView"),
  ]);
}

export const MODES: PaymentMode[] = [
  {
    id: "mode-om",
    name: "Orange Money",
    reference_required: true,
    active: true,
    display_order: 2,
    version: 1,
  },
  {
    id: "mode-cash",
    name: "Espèces",
    reference_required: false,
    active: true,
    display_order: 1,
    version: 1,
  },
];

function member(user_id: string, name: string, role: string): Member {
  return {
    user_id,
    name,
    phone: "+237677000000",
    role,
    default_location_id: null,
    active: true,
    locked: false,
    must_change_pin: false,
    version: 1,
  };
}

export const MEMBERS: Member[] = [
  member(OWNER_ID, "Awa Bello", "owner"),
  member(SELLER_ID, "Ibrahim Sali", "seller"),
  member(OTHER_SELLER_ID, "Paul Ndam", "seller"),
];

export function installment(overrides: Partial<Installment> = {}): Installment {
  return {
    id: "inst-1",
    number: "R-000001",
    paid_on: "2026-11-01",
    amount: 200000,
    mode_id: "mode-cash",
    reference: null,
    nature: "normal",
    status: "valid",
    to_refund: false,
    created_by: SELLER_ID,
    received_at: "2026-11-01T09:00:00Z",
    cancelled_at: null,
    cancelled_by: null,
    cancel_reason: null,
    ...overrides,
  };
}

/** Vente V-000124 à crédit : 800 000, acompte 200 000, reste 600 000. */
export function receivable(overrides: Partial<Receivable> = {}): Receivable {
  return {
    id: RECEIVABLE_ID,
    version: 1,
    customer: { id: CUSTOMER_ID, name: "Moussa Hamadou", phone: "+237690000001" },
    origin: "sale",
    sale_id: RECEIVABLE_ID,
    sale_number: "V-000124",
    sale_total: 1000000,
    paid_at_sale: 200000,
    description: null,
    initial_amount: 800000,
    total_paid: 200000,
    remaining: 600000,
    status: "open",
    opened_on: "2026-10-01",
    seniority_days: 41,
    seniority_band: "31_60",
    last_installment_on: "2026-11-01",
    responsible_seller_id: SELLER_ID,
    terms: null,
    attachment_ids: [],
    write_off: null,
    cancelled_on: null,
    manageable: false,
    installments: [installment()],
    reminders: [],
    guarantors: [],
    ...overrides,
  };
}

export function listing(items: Receivable[], overrides: Partial<ReceivableList["summary"]> = {}) {
  const open = items.filter((item) => item.status === "open");
  const summary = {
    total_due: open.reduce((sum, item) => sum + item.remaining, 0),
    debtor_count: new Set(open.map((item) => item.customer.id)).size,
    received_today: 0,
    ...overrides,
  };
  return { summary, items };
}

export type ReceivableRole = "owner" | "seller" | "accountant" | "driver";

/** Session ouverte et référentiels des Créances pour `role`. */
export function receivableRoutes(role: ReceivableRole): Record<string, Reply | Reply[]> {
  const userId = role === "owner" ? OWNER_ID : SELLER_ID;
  const name = role === "owner" ? "Awa Bello" : "Ibrahim Sali";
  const me = meBody({
    user_id: userId,
    name,
    shops: [{ shop_id: SHOP_A, shop_name: "Motos Garoua", role }],
  });
  return {
    [ROUTES.refresh]: json(200, tokenBody("t1")),
    [ROUTES.me]: json(200, me),
    [route("GET", "/payment-modes")]: json(200, MODES),
    [route("GET", "/members")]: json(200, MEMBERS),
    [LIST]: json(200, listing([receivable()])),
  };
}
