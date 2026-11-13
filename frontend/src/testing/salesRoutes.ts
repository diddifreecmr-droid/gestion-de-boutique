/**
 * Routes du faux serveur des ventes (tests seulement) : catalogue, ventes, reçu, membres,
 * demandes de prix (règles de la simulation) et retours (`salesReturnsRoutes.ts`).
 */
import type {
  PriceDecision,
  PriceRequestCommand,
  RecordSaleCommand,
  SaleResult,
} from "../core/gateways/salesContract";
import { receiptOf } from "../core/gateways/simulated/saleRecord";
import { apiError, json, SHOP_A, type Call } from "./fakeApi";
import { articleList, paymentModes, saleProfile, stockMatrix } from "./salesCatalog";
import { cancelled, page, reported } from "./salesFixtures";
import { listing, recordReturn } from "./salesReturnsRoutes";
import { addSale, type SaleServer } from "./salesServer";

function find(server: SaleServer, id: string): SaleResult | Response {
  return server.sales.get(id) ?? apiError(404, "NOT_FOUND", "Vente introuvable");
}

async function record(server: SaleServer, call: Call): Promise<Response> {
  const body = call.body as RecordSaleCommand;
  server.recordSale(SHOP_A, body);
  const capturedAt = call.headers.get("X-Captured-At");
  if (capturedAt === null) throw new Error("Faux serveur : X-Captured-At absent");
  return json(201, await addSale(server, body, new Date(capturedAt)));
}

async function servePriceRequests(
  server: SaleServer,
  method: string,
  route: string,
  call: Call,
): Promise<Response | null> {
  const sales = server.simulation.sales;
  if (route === "/price-requests") {
    if (method === "GET") return json(200, await sales.listPriceRequests(SHOP_A));
    const body = call.body as PriceRequestCommand;
    return json(201, await sales.requestPriceApproval(SHOP_A, body));
  }
  const match = /^\/price-requests\/([^/]+)(\/decision)?$/.exec(route);
  if (match?.[1] === undefined) return null;
  const id = decodeURIComponent(match[1]);
  if (method === "GET" && match[2] === undefined) {
    return json(200, await sales.getPriceRequest(SHOP_A, id));
  }
  const body = call.body as { decision: PriceDecision; version: number };
  return json(200, await sales.decidePriceRequest(SHOP_A, id, body.decision, body.version));
}

function onSale(server: SaleServer, method: string, id: string, action: string, call: Call) {
  const sale = find(server, id);
  if (sale instanceof Response) return sale;
  if (method === "GET" && action === "") return json(200, sale);
  if (method === "GET" && action === "/receipt") {
    const sequence = (server.printed.get(id) ?? 0) + 1;
    server.printed.set(id, sequence);
    return json(200, receiptOf(sale, sequence));
  }
  if (method === "GET" && action === "/returns") return json(200, listing(server, sale));
  if (method === "POST" && action === "/returns") return recordReturn(server, sale, call);
  if (method === "POST" && action === "/cancel") {
    if (server.role !== "owner") return apiError(403, "FORBIDDEN", "Réservé au propriétaire");
    if ((server.returns.get(id) ?? []).length > 0) {
      return apiError(409, "INVALID_STATE_TRANSITION", "Vente avec retour", { returns: 1 });
    }
    const next = cancelled(sale, (call.body as { reason: string }).reason);
    server.sales.set(id, next);
    return json(200, next);
  }
  if (method === "POST" && action === "/error-reports") {
    const body = call.body as { id: string; description: string };
    const { sale: next, report } = reported(sale, body.id, body.description);
    server.sales.set(id, next);
    return json(201, report);
  }
  return null;
}

export async function serveSales(
  server: SaleServer,
  method: string,
  path: string,
  call: Call,
): Promise<Response> {
  const [route = "", search = ""] = path.split("?");
  const query = new URLSearchParams(search);
  const q = query.get("q");
  if (method === "GET" && route === "/profile") {
    return json(200, {
      ...saleProfile(server.role, server.world.settings.minPriceRequiresApproval),
      exchange_days: server.exchange.days,
      employee_exchange_allowed: server.exchange.employeeAllowed,
    });
  }
  if (method === "GET" && route === "/payment-modes") return json(200, paymentModes());
  if (method === "GET" && route === "/stock") return json(200, stockMatrix(server.world, q));
  if (method === "GET" && route === "/members") return json(200, server.members);
  if (method === "GET" && route === "/articles") {
    return json(200, articleList(server.world, q, Number(query.get("limit") ?? "50")));
  }
  if (method === "GET" && route === "/customers") {
    return json(200, await server.simulation.sales.searchCustomers(SHOP_A, q ?? ""));
  }
  if (method === "POST" && route === "/sales") return record(server, call);
  const prices = await servePriceRequests(server, method, route, call);
  if (prices !== null) return prices;
  if (method === "GET" && route === "/sales") return json(200, page([...server.sales.values()]));
  const match = /^\/sales\/([^/]+)(\/[a-z-]+)?$/.exec(route);
  if (match?.[1] !== undefined) {
    const reply = onSale(server, method, decodeURIComponent(match[1]), match[2] ?? "", call);
    if (reply !== null) return reply;
  }
  throw new Error(`Faux serveur des ventes : route non prévue « ${method} ${path} »`);
}
