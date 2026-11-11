import { describe, expect, it, vi } from "vitest";
import { ApiError, NetworkError } from "../api/errors";
import type { ExpensesGateway, ExpenseCreate } from "../gateways/expensesContract";
import type { RecordSaleCommand, SaleResult, SalesGateway } from "../gateways/salesContract";
import type { OfflineCapture } from "./capture";
import type { OfflineSnapshot } from "./contract";
import { OfflineNotAllowed } from "./errors";
import {
  businessDayOf,
  withOfflineExpenses,
  withOfflineSales,
  type OfflineDeps,
} from "./offlineGateways";

const ARTICLE = "01890a5d-ac96-774b-bcce-b302099a8101";
const COMMAND: RecordSaleCommand = {
  id: "01890a5d-ac96-774b-bcce-b302099a9001",
  kind: "cash",
  lines: [
    { article_id: ARTICLE, quantity: "1", unit_price: 780_000, details: [{ color: "Rouge" }] },
  ],
  payments: [{ mode_id: "cash", amount: 780_000 }],
};
const EXPENSE: ExpenseCreate = { id: "01890a5d-ac96-774b-bcce-b302099a9002", amount: 5_000,
  category_id: "fuel", tags: [] }; // prettier-ignore
const SNAPSHOT = {
  articles: [{ id: ARTICLE, display_name: "Haojue HJ125-8", reference: null, stock_unit: "unit",
    sold_by_piece: false, base_price: 780_000, base_price_piece: null, min_price: 720_000,
    min_price_piece: null }],
} as OfflineSnapshot; // prettier-ignore

function deps(enabled: boolean, online: boolean, snapshot: OfflineSnapshot | null = SNAPSHOT) {
  const offline = {
    enabled: vi.fn(() => enabled),
    snapshot: vi.fn(() => Promise.resolve(snapshot)),
    queue: vi.fn((entry: { type: string }) =>
      Promise.resolve(entry.type === "sale.create" ? "V-HL-3F2A-0001" : "D-HL-3F2A-0001"),
    ),
  } as unknown as OfflineCapture; // seules ces trois méthodes servent aux passerelles
  const connectivity = { online, reportNetworkFailure: vi.fn(), reportResponse: vi.fn(),
    subscribe: vi.fn() }; // prettier-ignore
  const result: OfflineDeps = {
    offline,
    connectivity,
    deviceId: () => "dev",
    today: () => "2026-11-11",
  };
  return result;
}

function sales(record: SalesGateway["recordSale"]): SalesGateway {
  return { recordSale: record } as SalesGateway; // seule la saisie est enveloppée
}

const down = () => Promise.reject(new NetworkError("Failed to fetch"));

describe("droit inactif (V1) : comportement inchangé", () => {
  it("échec réseau → OfflineNotAllowed (une NetworkError), rien en file", async () => {
    const d = deps(false, false);
    const gateway = withOfflineSales(sales(vi.fn(down)), d);
    const error: unknown = await gateway
      .recordSale("A", COMMAND, new Date())
      .catch((e: unknown) => e);
    expect(error).toBeInstanceOf(OfflineNotAllowed);
    expect(error).toBeInstanceOf(NetworkError);
    expect((error as Error).cause).toBeInstanceOf(NetworkError);
    const expenses = withOfflineExpenses({ record: vi.fn(down) } as unknown as ExpensesGateway, d);
    await expect(expenses.record("A", EXPENSE)).rejects.toBeInstanceOf(OfflineNotAllowed);
    expect(d.offline.queue).not.toHaveBeenCalled();
  });

  it("succès et erreur métier passent tels quels", async () => {
    const sale = { number: "V-000001" } as SaleResult;
    const ok = withOfflineSales(sales(vi.fn(() => Promise.resolve(sale))), deps(false, true));
    expect(await ok.recordSale("A", COMMAND, new Date())).toBe(sale);
    const refused = new ApiError(422, "STOCK_INSUFFICIENT", "Stock insuffisant");
    const ko = withOfflineSales(sales(vi.fn(() => Promise.reject(refused))), deps(true, true));
    await expect(ko.recordSale("A", COMMAND, new Date())).rejects.toBe(refused);
  });
});

describe("droit actif : file hors connexion", () => {
  it("sans réseau : vente en file, reçu provisoire V-HL-…, aucun appel à l'API", async () => {
    const d = deps(true, false);
    const record = vi.fn(down);
    const sale = await withOfflineSales(sales(record), d).recordSale(
      "A", COMMAND, new Date("2026-11-11T10:00:00Z"),
    ); // prettier-ignore
    expect(record).not.toHaveBeenCalled();
    expect([sale.number, sale.provisional_number]).toEqual(["V-HL-3F2A-0001", "V-HL-3F2A-0001"]);
    expect(sale.lines[0]?.article_name).toBe("Haojue HJ125-8");
    expect([sale.total, sale.paid, sale.remaining]).toEqual([780_000, 780_000, 0]);
    expect(sale.warnings[0]?.code).toBe("OFFLINE_QUEUED");
    expect(d.offline.queue).toHaveBeenCalledWith(
      expect.objectContaining({ opId: COMMAND.id, type: "sale.create", payload: COMMAND }),
    );
  });

  it("l'envoi échoue faute de réseau : dépense en file ; instantané absent → refus", async () => {
    const d = deps(true, true);
    const expense = await withOfflineExpenses(
      { record: vi.fn(down) } as unknown as ExpensesGateway, d,
    ).record("A", EXPENSE); // prettier-ignore
    expect([expense.number, expense.amount, expense.spent_on]).toEqual([
      "D-HL-3F2A-0001",
      5_000,
      "2026-11-11",
    ]);
    const noSnapshot = withOfflineSales(sales(vi.fn(down)), deps(true, false, null));
    await expect(noSnapshot.recordSale("A", COMMAND, new Date())).rejects.toBeInstanceOf(
      OfflineNotAllowed,
    );
    const unknown = { ...COMMAND, lines: [{ quantity: "1", unit_price: 1, article_id: "x" }] };
    await expect(withOfflineSales(sales(vi.fn(down)), d).recordSale("A", unknown, new Date()))
      .rejects.toThrow(/absent de l'instantané/); // prettier-ignore
  });

  it("jour métier à Douala", () => {
    expect(businessDayOf(new Date("2026-11-11T23:30:00Z"))).toBe("2026-11-12");
  });
});
