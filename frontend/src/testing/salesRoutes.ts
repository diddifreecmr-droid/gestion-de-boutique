/** Routes du faux serveur des ventes (tests seulement) : catalogue, ventes, reçu, membres. */
import type { RecordSaleCommand, SaleResult } from "../core/gateways/salesContract";
import { receiptOf } from "../core/gateways/simulated/saleRecord";
import { apiError, json, SHOP_A, type Call } from "./fakeApi";
import { articleList, paymentModes, saleProfile, stockMatrix } from "./salesCatalog";
import { cancelled, page, reported } from "./salesFixtures";
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

function onSale(server: SaleServer, method: string, id: string, action: string, call: Call) {
  const sale = find(server, id);
  if (sale instanceof Response) return sale;
  if (method === "GET" && action === "") return json(200, sale);
  if (method === "GET" && action === "/receipt") {
    const sequence = (server.printed.get(id) ?? 0) + 1;
    server.printed.set(id, sequence);
    return json(200, receiptOf(sale, sequence));
  }
  if (method === "POST" && action === "/cancel") {
    if (server.role !== "owner") return apiError(403, "FORBIDDEN", "Réservé au propriétaire");
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
  if (method === "GET" && route === "/profile") return json(200, saleProfile(server.role));
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
  if (method === "GET" && route === "/sales") return json(200, page([...server.sales.values()]));
  const match = /^\/sales\/([^/]+)(\/[a-z-]+)?$/.exec(route);
  if (match?.[1] !== undefined) {
    const reply = onSale(server, method, decodeURIComponent(match[1]), match[2] ?? "", call);
    if (reply !== null) return reply;
  }
  throw new Error(`Faux serveur des ventes : route non prévue « ${method} ${path} »`);
}
