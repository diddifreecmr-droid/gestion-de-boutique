import "fake-indexeddb/auto";
import { Dexie } from "dexie";
import { afterEach, describe, expect, it } from "vitest";
import { openOfflineDb, SCHEMA_V1 } from "./db";
import { Outbox } from "./outbox";

const NAME = "boutique-offline-db-test";

afterEach(async () => {
  await Dexie.delete(NAME);
});

describe("base IndexedDB versionnée (specs § 7.3, OFF-10)", () => {
  it("la migration 1 → 2 garde la file et pose le statut « en attente »", async () => {
    const v1 = new Dexie(NAME);
    v1.version(1).stores(SCHEMA_V1);
    await v1.table("operations").bulkAdd([
      { shopId: "A", opId: "op-1", type: "sale.create", provisionalNumber: "V-HL-3F2A-0001",
        capturedAt: "2026-11-11T10:00:00.000Z", payload: {} },
      { shopId: "A", opId: "op-2", type: "expense.create", provisionalNumber: "D-HL-3F2A-0001",
        capturedAt: "2026-11-11T10:01:00.000Z", payload: {} },
    ]); // prettier-ignore
    await v1.table("counters").put({ key: "A|dev|V", value: 1 });
    v1.close();

    const db = openOfflineDb(NAME);
    const outbox = new Outbox(db);
    const pending = await outbox.pending("A");
    expect(pending.map((op) => [op.opId, op.status, op.error])).toEqual([
      ["op-1", "pending", null],
      ["op-2", "pending", null],
    ]);
    expect(await outbox.nextSequence("A", "dev", "V")).toBe(2);
    expect(db.verno).toBe(2);
    db.close();
  });

  it("file : ordre, refus gardé, retrait, abandon, instantané", async () => {
    const outbox = new Outbox(openOfflineDb(NAME));
    const base = { shopId: "A", type: "sale.create" as const, capturedAt: "", payload: {} };
    await outbox.enqueue({ ...base, opId: "1", provisionalNumber: "V-HL-3F2A-0001" });
    await outbox.enqueue({ ...base, opId: "2", provisionalNumber: "V-HL-3F2A-0002" });
    await outbox.enqueue({ ...base, shopId: "B", opId: "3", provisionalNumber: "V-HL-3F2A-0001" });
    await outbox.reject("1", { code: "PRICE_BELOW_MINIMUM", message: "Sous le minimum" });
    await expect(outbox.reject("absent", { code: "X", message: "m" })).rejects.toThrow(/absente/);
    expect((await outbox.pending("A")).map((op) => op.opId)).toEqual(["2"]);
    expect((await outbox.rejected("A"))[0]?.error?.code).toBe("PRICE_BELOW_MINIMUM");
    expect(await outbox.waiting()).toBe(2);
    await outbox.remove("2");
    expect(await outbox.snapshot("A")).toBeNull();
    const snapshot = { generated_at: "", since: null, full: true, min_price_enabled: false,
      articles: [], customers: [], expense_categories: [], locations: [], payment_modes: [] }; // prettier-ignore
    await outbox.saveSnapshot("A", snapshot, new Date());
    expect(await outbox.snapshot("A")).toEqual(snapshot);
    expect(await outbox.discardAll()).toBe(2);
    expect(await outbox.waiting()).toBe(0);
    outbox.db.close();
  });
});
