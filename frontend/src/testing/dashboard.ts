/**
 * Faux serveur du Tableau de bord et des accueils (tests seulement) : réponses typées par le
 * contrat généré. Jour de référence : mercredi 11/11/2026 à Douala.
 */
import type {
  Compared,
  Dashboard,
  DashboardDetail,
  Home,
  NotAvailable,
  PeriodOut,
  Valuation,
} from "../core/gateways/reportingContract";
import { profileBody } from "./catalog";
import { json, meBody, ROUTES, SHOP_A, tokenBody, type Reply } from "./fakeApi";

export const TODAY = "2026-11-11";
export const NOW = "2026-11-11T10:00:00Z";
export const HOME_PATH = `/s/${SHOP_A}`;
/** Tableau de bord complet du propriétaire, écran à part (specs § 15.1). */
export const DASHBOARD_PATH = `${HOME_PATH}/tableau-de-bord`;
export const API = `/api/v1/shops/${SHOP_A}`;
export const DASHBOARD_TODAY = `GET ${API}/dashboard?period=today`;
export const HOME = `GET ${API}/home`;
export const PRICE_REQUESTS = `GET ${API}/price-requests`;
export const PROFILE = `GET ${API}/profile`;

/** `GET /profile` avec les modules actifs donnés (le module `dashboard` par défaut). */
export function modulesProfile(
  modules: string[] = ["core", "audit", "catalog", "sales", "dashboard"],
) {
  return json(200, { ...profileBody("owner"), enabled_modules: modules });
}

export const detailRoute = (metric: string, query = "period=today") =>
  `GET ${API}/dashboard/details/${metric}?${query}`;

export const LOT_2: NotAvailable = { available: false, lot: 2, message: "Non disponible au Lot 1" };

export function compared(value: number, previous: number, change: string | null): Compared {
  return { value, previous, change_pct: change };
}

export function valuation(atWac: number | null, missing = 0): Valuation {
  return {
    at_wac: atWac,
    at_wac_known: atWac ?? 1_500_000,
    without_wac: missing,
    at_last_cost: atWac,
    at_last_cost_known: atWac ?? 1_500_000,
    without_last_cost: missing,
  };
}

export function period(kind: string, first: string, last: string, days: number): PeriodOut {
  return { kind, first_day: first, last_day: last, days };
}

/** Tableau du jour : 3 ventes à 2 340 000 (+12 % par rapport à hier), 1 vente sans coût. */
export function dashboardBody(overrides: Partial<Dashboard> = {}): Dashboard {
  return {
    period: period("today", TODAY, TODAY, 1),
    previous_period: period("today", "2026-11-10", "2026-11-10", 1),
    summary: {
      sales: compared(2_340_000, 2_089_286, "12.00"),
      sales_count: compared(3, 2, "50.00"),
      collected: compared(1_100_000, 0, null),
      margin: compared(610_000, 700_000, "-12.86"),
      margin_wac: compared(650_000, 720_000, "-9.72"),
      margin_gap: 40_000,
      margin_rate_pct: "26.07",
      without_cost: 1,
      expenses: compared(45_000, 30_000, "50.00"),
      result: compared(565_000, 670_000, "-15.67"),
    },
    series: null,
    receivables: {
      total_due: 1_800_000,
      debtor_count: 4,
      received: compared(200_000, 100_000, "100.00"),
      reminders_due: 2,
    },
    stock: {
      value: valuation(12_500_000),
      damaged: valuation(150_000),
      low_stock: 3,
      to_verify: 1,
      in_transit: LOT_2,
    },
    trucks: { trucks: LOT_2, transport_expenses: LOT_2 },
    alerts: { error_reports: 2, price_requests: 1 },
    ...overrides,
  };
}

/** Semaine du lundi 09/11 au mercredi 11/11 : série de 3 jours, marge négative le 10/11. */
export function weekBody(): Dashboard {
  return dashboardBody({
    period: period("week", "2026-11-09", TODAY, 3),
    previous_period: period("week", "2026-11-06", "2026-11-08", 3),
    series: {
      points: [
        { day: "2026-11-09", sales: 1_000_000, margin: 200_000 },
        { day: "2026-11-10", sales: 0, margin: -15_000 },
        { day: TODAY, sales: 2_340_000, margin: 610_000 },
      ],
      total_sales: 3_340_000,
      total_margin: 795_000,
      average_sales: 1_113_333,
      average_margin: 265_000,
    },
  });
}

export function detailBody(metric: string, lines: DashboardDetail["lines"], total: number) {
  const body: DashboardDetail = { metric, period: period("today", TODAY, TODAY, 1), total, lines };
  return body;
}

export function homeBody(role: "seller" | "accountant" | "driver"): Home {
  if (role === "seller") {
    return {
      role,
      today: TODAY,
      seller: { sales_count: 2, sales_amount: 1_540_000, reminders_due: 1, pending_uploads: 0 },
    };
  }
  if (role === "accountant") {
    return {
      role,
      today: TODAY,
      accountant: {
        transfers_to_receive: LOT_2,
        low_stock: 3,
        stock_value: valuation(12_500_000),
        expenses: 45_000,
      },
    };
  }
  return { role, today: TODAY, driver: { current_trip: LOT_2, trip_expenses: LOT_2 } };
}

/** Session ouverte dans la boutique A avec le rôle donné. */
export function signedInAs(role: string): Record<string, Reply> {
  return {
    [ROUTES.refresh]: json(200, tokenBody("t1")),
    [ROUTES.me]: json(
      200,
      meBody({ shops: [{ shop_id: SHOP_A, shop_name: "Motos Garoua", role }] }),
    ),
  };
}

/**
 * Écrans d'un rôle : session, `GET /home` ; propriétaire : tableau du jour, demandes de prix et
 * profil avec le module `dashboard` actif.
 */
export function homeRoutes(
  role: "owner" | "seller" | "accountant" | "driver",
  extra: Record<string, Reply | Reply[]> = {},
): Record<string, Reply | Reply[]> {
  const home =
    role === "owner"
      ? {
          [DASHBOARD_TODAY]: json(200, dashboardBody()),
          [PRICE_REQUESTS]: json(200, []),
          [PROFILE]: modulesProfile(),
        }
      : { [HOME]: json(200, homeBody(role)) };
  return { ...signedInAs(role), ...home, ...extra };
}

/** Charge à l'avance l'écran chargé à la demande (sous couverture, l'import est lent). */
export async function preloadDashboard(): Promise<void> {
  await Promise.all([
    import("../features/dashboard/HomeRoute"),
    import("../features/dashboard/DashboardRoute"),
    import("../features/sales/priceRequests/PriceRequestsHomeCard"),
  ]);
}
