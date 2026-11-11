/**
 * Faux serveur des Achats (tests seulement) : réponses typées par le contrat généré.
 * Heure de référence : 11/11/2026 à 11 h 00 à Douala.
 */
import { vi } from "vitest";
import type {
  Purchase,
  PurchaseLocation,
  PurchasePage,
  PurchasePaymentMode,
  Supplier,
} from "../core/gateways/purchasingContract";
import { HAOJUE_ID, profileBody, YAMAHA_ID } from "./catalog";
import { ARTICLES } from "./purchasingArticles";
import { json, meBody, ROUTES, SHOP_A, tokenBody, type Reply } from "./fakeApi";

type Role = "owner" | "accountant" | "seller" | "driver";
export type Routes = Record<string, Reply | Reply[]>;

export { HAOJUE_ID, YAMAHA_ID };
export { ARTICLES, WAX_ID, withArticleSearch } from "./purchasingArticles";
export const OWNER_ID = "01890a5d-ac96-774b-bcce-b302099a8000";
export const ACCOUNTANT_ID = "01890a5d-ac96-774b-bcce-b302099a8001";
export const PURCHASE_ID = "01890a5d-ac96-774b-bcce-b302099a8401";
export const NOW = "2026-11-11T10:00:00Z";
export const TODAY = "2026-11-11";
export const API = `/api/v1/shops/${SHOP_A}`;
export const PURCHASES_PATH = `/s/${SHOP_A}/achats`;
export const route = (method: string, path: string) => `${method} ${API}${path}`;

/** Charge à l'avance l'écran chargé à la demande (sous couverture, l'import dépasse 1 s). */
export async function preloadPurchasing(): Promise<void> {
  await import("../features/purchasing/PurchasingRoute");
}

/** Horloge contrôlable : seule `Date` est simulée (les minuteurs de userEvent restent réels). */
export function setClock(iso: string) {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(iso));
}

function place(id: string, name: string, order: number): PurchaseLocation {
  const base = { kind: "warehouse", is_point_of_sale: false, city: name, active: true };
  return { id, name, display_order: order, version: 1, ...base };
}

export const LOCATIONS: PurchaseLocation[] = [
  place("loc-gb", "Garoua-Boulaï", 1),
  place("loc-garoua", "Garoua", 2),
];

export const MODES: PurchasePaymentMode[] = [
  {
    id: "mode-cash",
    name: "Espèces",
    reference_required: false,
    active: true,
    display_order: 1,
    version: 1,
  },
  {
    id: "mode-virement",
    name: "Virement",
    reference_required: true,
    active: true,
    display_order: 2,
    version: 1,
  },
];

export function supplier(overrides: Partial<Supplier> = {}): Supplier {
  return {
    id: "sup-1",
    name: "Haojue Douala",
    phone: null,
    city: "Douala",
    country: "Cameroun",
    note: null,
    active: true,
    version: 1,
    ...overrides,
  };
}

export const SUPPLIERS: Supplier[] = [
  supplier(),
  supplier({ id: "sup-2", name: "Ancien Import", city: null, active: false }),
];

export function purchase(overrides: Partial<Purchase> = {}): Purchase {
  return {
    id: PURCHASE_ID,
    number: "A-000012",
    supplier_id: "sup-1",
    purchase_date: TODAY,
    location_id: "loc-gb",
    invoice_ref: null,
    invoice_photo_id: null,
    note: null,
    lines: [
      {
        article_id: HAOJUE_ID,
        quantity: "20",
        unit: "UNIT",
        stock_quantity: "20",
        stock_unit: "UNIT",
        unit_price: 520000,
        total: 10400000,
        fee_share: 400000,
        final_unit_cost: 540000,
      },
    ],
    fees: [{ kind: "customs", label: null, amount: 400000 }],
    article_count: 1,
    merchandise_total: 10400000,
    fees_total: 400000,
    total: 10800000,
    paid: 0,
    payment_status: "to_pay",
    payments: [],
    status: "valid",
    cancellation: null,
    created_by: ACCOUNTANT_ID,
    device_id: "dev-1",
    captured_at: "2026-11-11T09:00:00Z",
    received_at: "2026-11-11T09:00:00Z",
    editable: true,
    cancellable: false,
    last_correction_day: "2026-11-18",
    version: 1,
    ...overrides,
  };
}

export function page(items: Purchase[], overrides: Partial<PurchasePage> = {}): PurchasePage {
  const valid = items.filter((item) => item.status === "valid");
  const sum = (pick: (p: Purchase) => number) => valid.reduce((total, p) => total + pick(p), 0);
  return {
    items,
    next_cursor: null,
    first_day: "2026-11-01",
    last_day: "2026-11-30",
    totals: {
      count: valid.length,
      merchandise: sum((p) => p.merchandise_total),
      fees: sum((p) => p.fees_total),
      total: sum((p) => p.total),
      paid: sum((p) => p.paid),
    },
    ...overrides,
  };
}

/** Session ouverte et référentiels des Achats pour `role`. */
export function purchasingRoutes(role: Role, extra: Routes = {}): Routes {
  const userId = role === "owner" ? OWNER_ID : ACCOUNTANT_ID;
  const me = meBody({
    user_id: userId,
    shops: [{ shop_id: SHOP_A, shop_name: "Motos Garoua", role }],
  });
  const articles = Object.fromEntries(
    ARTICLES.map((article) => [route("GET", `/articles/${article.id}`), json(200, article)]),
  );
  return {
    [ROUTES.refresh]: json(200, tokenBody("t1")),
    [ROUTES.me]: json(200, me),
    [route("GET", "/suppliers")]: json(200, { items: SUPPLIERS }),
    [route("GET", "/locations")]: json(200, { items: LOCATIONS, read_only: role !== "owner" }),
    [route("GET", "/payment-modes")]: json(200, MODES),
    [route("GET", "/settings")]: json(200, { reception_location_id: "loc-gb" }),
    [route("GET", "/profile")]: json(200, profileBody(role === "owner" ? "owner" : "accountant")),
    [route("GET", "/purchases")]: json(200, page([])),
    ...articles,
    ...extra,
  };
}
