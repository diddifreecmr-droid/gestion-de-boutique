import { describe, expect, it, vi } from "vitest";
import type { Customer, CustomersGateway } from "../../core/gateways/customersContract";
import type { SalePage, SaleResult, SalesGateway } from "../../core/gateways/salesContract";
import { CASH_CUSTOMER, loadTodaySales, RECENT_LIMIT } from "./todaySales";

function sale(n: number, customerId: string | null = null): SaleResult {
  return {
    id: `sale-${String(n)}`,
    number: `V-${String(n)}`,
    status: "valid",
    kind: customerId === null ? "cash" : "credit",
    sold_at: "2026-11-11T09:00:00Z",
    customer_id: customerId,
    total: 1000 * n,
  } as SaleResult;
}

function gateways(items: SaleResult[], customers: Partial<Customer>[] = []) {
  const page = { items, totals: { count: items.length, total: 99_000, paid: 0 } } as SalePage;
  const listSales = vi.fn<SalesGateway["listSales"]>(() => Promise.resolve(page));
  const search = vi.fn<CustomersGateway["search"]>(() => Promise.resolve(customers as Customer[]));
  return {
    deps: {
      sales: { listSales } as unknown as SalesGateway,
      customers: { search } as unknown as CustomersGateway,
    },
    listSales,
    search,
  };
}

describe("chiffres de la page d'accueil (specs § 15.1)", () => {
  it("total du serveur, 5 dernières ventes au plus, « Comptant » sans lecture des clients", async () => {
    const { deps, listSales, search } = gateways([1, 2, 3, 4, 5, 6, 7].map((n) => sale(n)));
    const today = await loadTodaySales(deps, "shop");
    expect(RECENT_LIMIT).toBe(5);
    expect(today.total).toBe(99_000);
    expect(today.count).toBe(7);
    expect(today.recent.map((s) => s.number)).toEqual(["V-1", "V-2", "V-3", "V-4", "V-5"]);
    expect(today.recent.every((s) => s.customer === CASH_CUSTOMER)).toBe(true);
    expect(listSales).toHaveBeenCalledWith("shop", {}, null);
    expect(search).not.toHaveBeenCalled();
  });

  it("nom du client lu une fois ; seules les clés utiles sortent (aucun coût ni marge)", async () => {
    const withCost = { ...sale(1, "cus-1"), lines: [{ margin: 5, frozen_wac: 1 }] } as SaleResult;
    const { deps, search } = gateways([withCost, sale(2, "cus-1")], [{ id: "cus-1", name: "Awa" }]);
    const today = await loadTodaySales(deps, "shop");
    expect(today.recent.map((s) => s.customer)).toEqual(["Awa", "Awa"]);
    expect(search).toHaveBeenCalledOnce();
    expect(Object.keys(today.recent[0] ?? {}).sort()).toEqual(
      ["cancelled", "credit", "customer", "id", "number", "soldAt", "total"].sort(),
    );
  });

  it("client introuvable : erreur explicite (fail-fast)", async () => {
    const { deps } = gateways([sale(3, "cus-x")]);
    await expect(loadTodaySales(deps, "shop")).rejects.toThrow(
      "Client cus-x de la vente V-3 introuvable",
    );
  });
});
