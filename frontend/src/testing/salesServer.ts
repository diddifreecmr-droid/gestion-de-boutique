/**
 * Faux serveur HTTP des ventes (tests seulement) : les routes `/shops/{id}/…` de T16a servies
 * au-dessus du monde simulé (mêmes règles que la vitrine : stock, minimum, châssis, plafond).
 * Les écrans passent donc par la **vraie** passerelle (`httpSales`, `httpCatalog`) et le vrai
 * client (`X-Captured-At`, enveloppe d'erreur). Une route non prévue fait échouer le test.
 */
import { vi } from "vitest";
import { ApiError } from "../core/api/errors";
import type { Gateways } from "../core/gateways/gateways";
import { createSimulation } from "../core/gateways/simulated";
import type { World } from "../core/gateways/simulated/world";
import type { SaleReturn, SaleReturnCommand } from "../core/gateways/returnsContract";
import type { RecordSaleCommand, SaleMember, SaleResult } from "../core/gateways/salesContract";
import { apiError, json, meBody, ROUTES, SHOP_A, tokenBody, type Reply } from "./fakeApi";
import { NOW, withCosts } from "./salesFixtures";
import { serveSales } from "./salesRoutes";

export type SaleRole = "owner" | "seller";
export type Routes = Record<string, Reply | Reply[]>;

export const SALE_SHOP = SHOP_A;
export const API = `/api/v1/shops/${SHOP_A}`;
export const SELLER_ID = "01890a5d-ac96-774b-bcce-b302099a8010";
export const OWNER_ID = "01890a5d-ac96-774b-bcce-b302099a8000";

export interface SaleServer {
  role: SaleRole;
  userId: string;
  routes: Routes;
  /** Réseau des routes de la boutique (la session, elle, reste joignable). */
  network: { online: boolean };
  /** Appelé à chaque `POST /sales` reçu : `(shopId, corps)`. */
  recordSale: ReturnType<typeof vi.fn<(shopId: string, body: RecordSaleCommand) => void>>;
  world: World;
  simulation: Gateways;
  /** Ventes telles que le rôle les reçoit, par `id`. */
  sales: Map<string, SaleResult>;
  printed: Map<string, number>;
  members: SaleMember[];
  /** Retours enregistrés, par vente. */
  returns: Map<string, SaleReturn[]>;
  /** Appelé à chaque `POST /sales/{id}/returns` reçu : `(saleId, corps)`. */
  recordReturn: ReturnType<typeof vi.fn<(saleId: string, body: SaleReturnCommand) => void>>;
  /** Réglages d'échange servis par `/profile` et appliqués aux échanges (QC-4). */
  exchange: { days: number | null; employeeAllowed: boolean };
}

export function member(id: string, name: string, role: string): SaleMember {
  const base = { phone: "+237690000009", default_location_id: null, active: true };
  return { user_id: id, name, role, locked: false, ...base } as SaleMember;
}

function fromError(error: unknown): Response {
  if (error instanceof ApiError) {
    return apiError(error.status, error.code, error.message, { ...error.details });
  }
  throw error;
}

/**
 * Session ouverte pour `role` et routes de vente. `extra` remplace une route précise
 * (clé exacte `"GET /api/v1/shops/…/sales"`) ; tout le reste est servi par le monde simulé.
 */
export function saleServer(role: SaleRole, extra: Routes = {}): SaleServer {
  const network = { online: true };
  const me = meBody({
    user_id: role === "owner" ? OWNER_ID : SELLER_ID,
    shops: [{ shop_id: SHOP_A, shop_name: "Motos Garoua", role }],
  });
  const base: Routes = {
    [ROUTES.refresh]: json(200, tokenBody("t1")),
    [ROUTES.me]: json(200, me),
    ...extra,
  };
  const userId = role === "owner" ? OWNER_ID : SELLER_ID;
  const { world, gateways } = createSimulation({
    isOnline: () => true,
    roleIn: () => role,
    userIn: () => userId,
  });
  const server: SaleServer = {
    role,
    userId,
    routes: base,
    network,
    recordSale: vi.fn(),
    world,
    simulation: gateways,
    sales: new Map(),
    printed: new Map(),
    returns: new Map(),
    recordReturn: vi.fn(),
    exchange: { days: null, employeeAllowed: false },
    members: [member(OWNER_ID, "Awa Bello", "owner"), member(SELLER_ID, "Issa Vendeur", "seller")],
  };
  server.routes = new Proxy(base, {
    get(target, key) {
      if (typeof key !== "string" || key in target) return Reflect.get(target, key) as unknown;
      const at = key.indexOf(` ${API}`);
      if (at < 0) return undefined;
      if (!network.online) return new TypeError("Failed to fetch");
      const method = key.slice(0, at);
      const path = key.slice(at + 1 + API.length);
      const reply: Reply = (call) => serveSales(server, method, path, call).catch(fromError);
      return reply;
    },
  });
  return server;
}

/** Enregistre une vente côté serveur avant le rendu (même chemin que `POST /sales`). */
export async function addSale(
  server: SaleServer,
  command: RecordSaleCommand,
  at: Date = new Date(NOW),
): Promise<SaleResult> {
  const sale = await server.simulation.sales.recordSale(SHOP_A, command, at);
  const shown: SaleResult = { ...sale, seller_id: server.userId, created_by: server.userId };
  const view = server.role === "owner" ? withCosts(shown) : shown;
  server.sales.set(view.id, view);
  return view;
}
