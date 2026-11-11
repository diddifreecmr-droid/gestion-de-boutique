import { describe, expect, it, vi } from "vitest";
import { ApiError, NetworkError } from "../../api/errors";
import { createSimulatedGateways } from ".";
import type { RecordSaleCommand } from "../salesContract";

const SHOP = "s1";
const AT = new Date("2026-11-11T10:00:00Z");

function gateways(online = true, role: "seller" | "owner" = "seller") {
  const onNetworkFailure = vi.fn();
  const value = createSimulatedGateways({
    isOnline: () => online,
    roleIn: () => role,
    onNetworkFailure,
  });
  return { ...value, onNetworkFailure };
}

function command(overrides: Partial<RecordSaleCommand> = {}): RecordSaleCommand {
  return {
    id: "0193a7c2-0000-7000-8000-000000000001",
    location_id: "loc-garoua",
    sold_on: "2026-11-10",
    kind: "cash",
    customer: null,
    lines: [
      {
        article_id: "art-hj125-8",
        sale_mode: "unit",
        quantity: "1",
        unit_price: 780_000,
        details: [],
      },
    ],
    payments: [{ mode_id: "pm-cash", amount: 780_000, reference: null }],
    credit: null,
    price_request_id: null,
    note: null,
    ...overrides,
  };
}

async function codeOf(promise: Promise<unknown>): Promise<string> {
  try {
    await promise;
  } catch (error) {
    if (error instanceof ApiError) return error.code;
    throw error;
  }
  throw new Error("La promesse aurait dû être rejetée");
}

describe("passerelle de vente simulée", () => {
  it("numérote V-000124 puis V-000125 et rejoue une vente déjà reçue (idempotence)", async () => {
    const { sales } = gateways();
    const first = await sales.recordSale(SHOP, command(), AT);
    expect(first).toMatchObject({
      number: "V-000124",
      total: 780_000,
      paid: 780_000,
      remaining: 0,
    });
    expect(first.receivable).toBeNull();
    expect(await sales.recordSale(SHOP, command(), AT)).toBe(first);
    const second = await sales.recordSale(SHOP, command({ id: "autre" }), AT);
    expect(second.number).toBe("V-000125");
  });

  it("le stock baisse après la vente : la recherche suivante le montre", async () => {
    const { sales, catalog } = gateways();
    await sales.recordSale(SHOP, command(), AT);
    const { items } = await catalog.searchArticles(SHOP, {
      location_id: "loc-garoua",
      query: "hj125",
      limit: 5,
    });
    expect(items[0]?.available).toBe("3");
  });

  it("refuse les formes invalides (VALIDATION_ERROR)", async () => {
    const { sales } = gateways();
    expect(await codeOf(sales.recordSale(SHOP, command({ lines: [] }), AT))).toBe(
      "VALIDATION_ERROR",
    );
    const half = command({ payments: [{ mode_id: "pm-cash", amount: 1, reference: null }] });
    expect(await codeOf(sales.recordSale(SHOP, half, AT))).toBe("PAYMENT_INCOMPLETE");
    const noCustomer = command({ kind: "credit", payments: [] });
    expect(await codeOf(sales.recordSale(SHOP, noCustomer, AT))).toBe("VALIDATION_ERROR");
    const over = command({ payments: [{ mode_id: "pm-cash", amount: 900_000, reference: null }] });
    expect(await codeOf(sales.recordSale(SHOP, over, AT))).toBe("OVERPAYMENT");
    const badQuantity = command({
      lines: [
        {
          article_id: "art-hj125-8",
          sale_mode: "unit",
          quantity: "1.5",
          unit_price: 1,
          details: [],
        },
      ],
    });
    expect(await codeOf(sales.recordSale(SHOP, badQuantity, AT))).toBe("VALIDATION_ERROR");
  });

  it("hors connexion : NetworkError et signal au bandeau, rien n'est enregistré", async () => {
    const { sales, onNetworkFailure } = gateways(false);
    await expect(sales.recordSale(SHOP, command(), AT)).rejects.toBeInstanceOf(NetworkError);
    expect(onNetworkFailure).toHaveBeenCalledTimes(1);
  });

  it("recherche de clients par nom ou téléphone", async () => {
    const { sales } = gateways();
    expect((await sales.searchCustomers(SHOP, "")).items).toEqual([]);
    expect((await sales.searchCustomers(SHOP, "aissa")).items.map((c) => c.id)).toEqual([
      "cus-aissatou",
    ]);
    expect((await sales.searchCustomers(SHOP, "699 88")).items.map((c) => c.id)).toEqual([
      "cus-aissatou",
    ]);
  });

  it("refuse une limite de recherche invalide et un article inconnu", async () => {
    const { catalog, sales } = gateways();
    await expect(
      catalog.searchArticles(SHOP, { location_id: "loc-garoua", query: "", limit: 0 }),
    ).rejects.toThrow("limite de recherche invalide");
    await expect(
      sales.requestPriceApproval(SHOP, {
        id: "p1",
        location_id: "loc-garoua",
        article_id: "inconnu",
        requested_price: 1,
      }),
    ).rejects.toThrow("article inconnu");
  });
});
