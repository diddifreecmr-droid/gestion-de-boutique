/**
 * Faux serveur des Dépenses (tests seulement) : réponses typées par le contrat généré.
 * Heure de référence : 11/11/2026 à 11 h 00 à Douala ; minuit de ce jour = 23:00 UTC.
 */
import { vi } from "vitest";
import type {
  Expense,
  ExpenseCategory,
  ExpensePage,
  Location,
  Member,
  PaymentMode,
} from "../core/gateways/expensesContract";
import { json, meBody, ROUTES, SHOP_A, tokenBody, type Reply } from "./fakeApi";

export const OWNER_ID = "01890a5d-ac96-774b-bcce-b302099a8000";
export const ACCOUNTANT_ID = "01890a5d-ac96-774b-bcce-b302099a8001";
export const NOW = "2026-11-11T10:00:00Z";
export const TODAY = "2026-11-11";
/** Minuit (Douala) qui clôt le 11/11/2026. */
export const DEADLINE = "2026-11-11T23:00:00+00:00";

export const API = `/api/v1/shops/${SHOP_A}`;
export const route = (method: string, path: string) => `${method} ${API}${path}`;

/**
 * Charge à l'avance l'écran chargé à la demande : sous couverture et en parallèle, sa
 * première importation dépasse le délai des `findBy` (1 s).
 */
export async function preloadExpenses(): Promise<void> {
  await import("../features/expenses/ExpensesRoute");
}

/** Horloge contrôlable : seule `Date` est simulée (les minuteurs de userEvent restent réels). */
export function setClock(iso: string) {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(iso));
}

function category(id: string, name: string, order: number, extra: Partial<ExpenseCategory> = {}) {
  return {
    id,
    name,
    is_base: true,
    active: true,
    requires_description: false,
    display_order: order,
    version: 1,
    ...extra,
  };
}

export const CATEGORIES: ExpenseCategory[] = [
  category("cat-carburant", "Carburant", 1),
  category("cat-repas", "Repas", 2),
  category("cat-salaire", "Salaire", 3),
  category("cat-loyer", "Loyer", 4),
  category("cat-autre", "Autre", 5, { requires_description: true }),
  category("cat-groupe", "Groupe électrogène", 6, { is_base: false }),
];

export const MODES: PaymentMode[] = [
  {
    id: "mode-om",
    name: "Orange Money",
    reference_required: false,
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

export const LOCATIONS: Location[] = [
  {
    id: "loc-garoua",
    name: "Boutique Garoua",
    kind: "shop",
    is_point_of_sale: true,
    city: "Garoua",
    display_order: 1,
    active: true,
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
  member(ACCOUNTANT_ID, "Paul Ndam", "accountant"),
];

export function expense(overrides: Partial<Expense> = {}): Expense {
  return {
    id: "exp-12",
    number: "D-000012",
    spent_on: TODAY,
    amount: 15000,
    category_id: "cat-carburant",
    payment_mode_id: "mode-cash",
    tags: [],
    description: null,
    location_id: null,
    beneficiary: null,
    attachment_id: null,
    status: "valid",
    created_by: ACCOUNTANT_ID,
    device_id: "dev-1",
    captured_at: "2026-11-11T09:00:00Z",
    received_at: "2026-11-11T09:00:00Z",
    cancellation: null,
    editable: true,
    correction_deadline: DEADLINE,
    version: 1,
    ...overrides,
  };
}

export function page(items: Expense[], overrides: Partial<ExpensePage> = {}): ExpensePage {
  const valid = items.filter((item) => item.status === "valid");
  const amount = valid.reduce((sum, item) => sum + item.amount, 0);
  const byCategory = new Map<string, { amount: number; count: number }>();
  for (const item of valid) {
    const current = byCategory.get(item.category_id) ?? { amount: 0, count: 0 };
    byCategory.set(item.category_id, {
      amount: current.amount + item.amount,
      count: current.count + 1,
    });
  }
  return {
    items,
    next_cursor: null,
    first_day: TODAY,
    last_day: TODAY,
    totals: {
      amount,
      count: valid.length,
      by_category: [...byCategory].map(([category_id, total]) => ({ category_id, ...total })),
    },
    ...overrides,
  };
}

export type ExpenseRole = "owner" | "accountant" | "seller" | "driver";

/** Session ouverte et référentiels des Dépenses pour `role`. */
export function expenseRoutes(role: ExpenseRole): Record<string, Reply | Reply[]> {
  const userId = role === "owner" ? OWNER_ID : ACCOUNTANT_ID;
  const name = role === "owner" ? "Awa Bello" : "Paul Ndam";
  const me = meBody({
    user_id: userId,
    name,
    shops: [{ shop_id: SHOP_A, shop_name: "Motos Garoua", role }],
  });
  return {
    [ROUTES.refresh]: json(200, tokenBody("t1")),
    [ROUTES.me]: json(200, me),
    [route("GET", "/expense-categories")]: json(200, CATEGORIES),
    [route("GET", "/payment-modes")]: json(200, MODES),
    [route("GET", "/locations")]: json(200, { items: LOCATIONS, read_only: role !== "owner" }),
    [route("GET", "/members")]: json(200, MEMBERS),
    [route("GET", "/expenses")]: json(200, page([])),
  };
}

export const EXPENSES_PATH = `/s/${SHOP_A}/depenses`;
