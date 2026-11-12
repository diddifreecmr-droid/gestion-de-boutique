/**
 * Faux serveur des écrans Alertes, Journal, Clients et console plateforme (tests seulement) :
 * réponses typées par le contrat généré.
 */
import type { Alert, AlertPage } from "../core/gateways/alertsContract";
import type { Customer, CustomerSale, CustomerSheet } from "../core/gateways/customersContract";
import type { AuditEntry } from "../core/gateways/journalContract";
import type { ShopAccess, ShopSummary } from "../core/gateways/platformContract";
import { json, meBody, ROUTES, SHOP_A, tokenBody, type Reply } from "./fakeApi";
import { MEMBERS, OWNER_ID, SELLER_ID } from "./receivables";

export const API = `/api/v1/shops/${SHOP_A}`;
export const route = (method: string, path: string) => `${method} ${API}${path}`;
export const SHOP_PATH = `/s/${SHOP_A}`;

/** Charge à l'avance les écrans chargés à la demande (sous couverture, l'import est lent). */
export async function preloadLot1Screens(): Promise<void> {
  await Promise.all([
    import("../features/alerts/AlertsRoute"),
    import("../features/journal/JournalRoute"),
    import("../features/customers/CustomersRoute"),
    import("../features/platform/PlatformConsole"),
  ]);
}

export type ShopRole = "owner" | "seller" | "accountant" | "driver";

/** Session restaurée d'un membre de « Motos Garoua ». */
export function memberSession(role: ShopRole): Record<string, Reply | Reply[]> {
  const userId = role === "owner" ? OWNER_ID : SELLER_ID;
  const me = meBody({
    user_id: userId,
    name: role === "owner" ? "Awa Bello" : "Ibrahim Sali",
    shops: [{ shop_id: SHOP_A, shop_name: "Motos Garoua", role }],
  });
  return { [ROUTES.refresh]: json(200, tokenBody("t1")), [ROUTES.me]: json(200, me) };
}

export function alert(overrides: Partial<Alert> = {}): Alert {
  return {
    id: "alert-1",
    type: "low_stock",
    entity: { type: "article", id: "art-1", number: "Haojue HJ125-8" },
    message: "Stock bas : Haojue HJ125-8 (1 restant à Garoua)",
    read: false,
    active: true,
    created_at: "2026-11-11T09:30:00Z",
    ...overrides,
  };
}

export function alertPage(items: Alert[], next: string | null = null): AlertPage {
  return { items, next_cursor: next, unread_count: items.filter((a) => !a.read).length };
}

export function entry(overrides: Partial<AuditEntry> = {}): AuditEntry {
  return {
    id: "aud-1",
    captured_at: "2026-11-10T13:32:00Z",
    received_at: "2026-11-10T13:32:05Z",
    performer: { user_id: SELLER_ID, role: "seller", device_id: "dev-1" },
    action: "create",
    action_label: "Créer",
    module: "sales",
    entity: { type: "sale", id: "sale-124", number: "V-000124" },
    summary: "1 moto Haojue HJ125-8, 780 000 FCFA",
    changes: [],
    reason: null,
    sensitive: false,
    ...overrides,
  };
}

export const JOURNAL_ROUTES = { [route("GET", "/members")]: json(200, MEMBERS) };

export function customer(overrides: Partial<Customer> = {}): Customer {
  return {
    id: "cust-moussa",
    name: "Moussa Hamadou",
    phone: "+237690000001",
    kind: "individual",
    city: "Garoua",
    address: null,
    id_doc_type: null,
    id_doc_number: null,
    id_doc_photo_id: null,
    credit_limit: null,
    note: null,
    created_by: OWNER_ID,
    version: 3,
    ...overrides,
  };
}

/** Vente de la fiche client : montants de vente seulement (aucun coût). */
export function customerSale(overrides: Partial<CustomerSale> = {}): CustomerSale {
  return {
    id: "sale-124",
    number: "V-000124",
    provisional_number: null,
    status: "valid",
    kind: "credit",
    sold_on: "2026-10-01",
    sold_at: "2026-10-01T10:00:00Z",
    location_id: "loc-1",
    seller_id: SELLER_ID,
    customer_id: "cust-moussa",
    total: 1000000,
    paid: 400000,
    remaining: 600000,
    receivable: { id: "sale-124", remaining: 600000 },
    lines: [],
    payments: [],
    credit: null,
    note: null,
    stock_to_verify: false,
    cancellation: null,
    created_by: SELLER_ID,
    device_id: "dev-1",
    captured_at: "2026-10-01T10:00:00Z",
    received_at: "2026-10-01T10:00:01Z",
    editable: false,
    version: 1,
    warnings: [],
    error_reports: [],
    ...overrides,
  };
}

export function customerSheet(overrides: Partial<CustomerSheet> = {}): CustomerSheet {
  return {
    customer: customer(),
    total_bought: 1000000,
    total_due: 600000,
    sales: [],
    ...overrides,
  };
}

export const ADMIN_SHOP_ID = "01890a5d-ac96-774b-bcce-b302099a8057";
export const PLATFORM = "/api/v1/platform/shops";

export function shopSummary(overrides: Partial<ShopSummary> = {}): ShopSummary {
  return {
    shop_id: ADMIN_SHOP_ID,
    name: "Motos Garoua",
    profile_code: "motos",
    city: "Garoua",
    status: "active",
    enabled_modules: ["audit", "catalog", "core", "sales"],
    account_id: "acc-1",
    account_name: "Moussa",
    plan: "free",
    created_at: "2026-11-01T08:00:00Z",
    ...overrides,
  };
}

export function shopAccess(overrides: Partial<ShopAccess> = {}): ShopAccess {
  return {
    shop_id: ADMIN_SHOP_ID,
    entitlements: [{ code: "offline_capture", enabled: false, override: null }],
    admin_access_until: null,
    ...overrides,
  };
}

/** Session de l'administrateur plateforme, liste des boutiques. */
export function adminSession(
  shops: ShopSummary[] = [shopSummary()],
): Record<string, Reply | Reply[]> {
  return {
    [ROUTES.refresh]: json(200, tokenBody("t1")),
    [ROUTES.me]: json(200, meBody({ is_platform_admin: true, shops: [] })),
    [`GET ${PLATFORM}`]: json(200, shops),
  };
}
