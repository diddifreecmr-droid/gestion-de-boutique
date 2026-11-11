import "fake-indexeddb/auto";
import { Dexie } from "dexie";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, NetworkError } from "../api/errors";
import { createOfflineCapture, type CaptureDeps } from "./capture";
import type { OfflineSnapshot, SyncRequest, SyncResult } from "./contract";
import * as engine from "./engine";
import { createOfflineRights } from "./rights";

const DEVICE = "01890a5d-ac96-774b-bcce-b302099a3f2a";
const NAME = "boutique-offline-capture-test";
const SNAPSHOT: OfflineSnapshot = {
  generated_at: "2026-11-11T10:00:00Z",
  since: null,
  full: true,
  min_price_enabled: true,
  articles: [],
  customers: [],
  expense_categories: [],
  locations: [],
  payment_modes: [],
};

function storage() {
  const data = new Map<string, string>();
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => void data.set(key, value),
    removeItem: (key: string) => void data.delete(key),
  };
}

type Answer = (op: SyncRequest["operations"][number]) => SyncResult;

function setup(answer: Answer = accept, enabled = true) {
  const rights = createOfflineRights(storage);
  if (enabled) rights.note("A", { offline_capture: true });
  const sent: SyncRequest[] = [];
  const load = vi.fn(() =>
    Promise.resolve({ ...engine, openOutbox: () => engine.openOutbox(NAME) }),
  );
  const deps: CaptureDeps = {
    rights,
    deviceId: () => DEVICE,
    send: vi.fn((_shopId: string, body: SyncRequest) => {
      sent.push(body);
      return Promise.resolve({ results: body.operations.map(answer) });
    }),
    fetchSnapshot: vi.fn(() => Promise.resolve(SNAPSHOT)),
    load,
  };
  return { capture: createOfflineCapture(deps), deps, sent, load };
}

let counter = 0;
function accept(op: SyncRequest["operations"][number]): SyncResult {
  counter += 1;
  return {
    op_id: op.op_id,
    status: "accepted",
    provisional_number: op.provisional_number ?? null,
    number: `V-${String(counter).padStart(6, "0")}`,
    entity_id: op.op_id,
    warnings: [],
    error: null,
  };
}

const queueSale = (capture: ReturnType<typeof setup>["capture"], opId: string) =>
  capture.queue({
    shopId: "A",
    opId,
    type: "sale.create",
    capturedAt: new Date("2026-11-11T10:00:00Z"),
    payload: { id: opId },
  });

afterEach(async () => {
  counter = 0;
  await Dexie.delete(NAME);
});

describe("droit inactif (V1) : inerte", () => {
  it("rien n'est chargé, rien n'est envoyé, aucune file", async () => {
    const { capture, load, deps } = setup(accept, false);
    expect(await capture.waiting()).toBe(0);
    expect(await capture.discard()).toBe(0);
    const stop = capture.watch("A", window);
    stop();
    await expect(queueSale(capture, "op")).rejects.toThrow(/non ouverte/);
    await expect(capture.syncNow("A")).rejects.toThrow(/non ouverte/);
    expect(load).not.toHaveBeenCalled();
    expect(deps.send).not.toHaveBeenCalled();
  });
});

describe("droit actif : file, ordre, lots, résultats", () => {
  it("numéros provisoires suivis, envoi dans l'ordre par lots de 20, arrivées notées", async () => {
    const { capture, sent } = setup();
    const numbers: string[] = [];
    for (let i = 1; i <= 21; i += 1) numbers.push(await queueSale(capture, `op-${String(i)}`));
    expect(numbers[0]).toBe("V-HL-3F2A-0001");
    expect(numbers[20]).toBe("V-HL-3F2A-0021");
    expect(capture.state.get().pending["A"]).toBe(21);
    expect(await capture.waiting()).toBe(21);
    await capture.syncNow("A");
    expect(sent.map((body) => body.operations.length)).toEqual([20, 1]);
    expect(sent[0]?.operations.map((op) => op.op_id).slice(0, 2)).toEqual(["op-1", "op-2"]);
    expect(sent[0]?.device_id).toBe(DEVICE);
    expect(capture.state.get().pending["A"]).toBe(0);
    expect(capture.state.get().arrived[0]).toBe("Vente V-HL-3F2A-0001 → V-000001");
    expect(await capture.snapshot("A")).toEqual(SNAPSHOT);
  });

  it("refus gardé avec son motif, doublon retiré, les suivantes passent", async () => {
    const { capture } = setup((op) =>
      op.op_id === "bad"
        ? { ...accept(op), status: "rejected", number: null,
            error: { code: "PRICE_BELOW_MINIMUM", message: "Prix sous le minimum", details: {} } }
        : { ...accept(op), status: op.op_id === "dup" ? "duplicate" : "accepted" },
    ); // prettier-ignore
    for (const id of ["ok", "bad", "dup"]) await queueSale(capture, id);
    await capture.syncNow("A");
    const state = capture.state.get();
    expect(state.pending["A"]).toBe(0);
    expect(state.rejected["A"]).toEqual([
      { number: "V-HL-3F2A-0002", message: "Prix sous le minimum" },
    ]);
    expect(state.arrived).toHaveLength(2);
  });

  it("sans réseau la file reste ; autre erreur montrée puis relancée ; abandon (RG-T24)", async () => {
    const { capture, deps } = setup();
    await queueSale(capture, "op-1");
    vi.mocked(deps.send).mockRejectedValueOnce(new NetworkError("hors ligne"));
    await capture.syncNow("A");
    expect(capture.state.get().pending["A"]).toBe(1);
    expect(capture.state.get().failure).toBeNull();
    const refused = new ApiError(403, "FEATURE_DISABLED", "Fonction non disponible");
    vi.mocked(deps.send).mockRejectedValueOnce(refused);
    await expect(capture.syncNow("A")).rejects.toBe(refused);
    expect(capture.state.get().failure).toBe("Fonction non disponible");
    expect(await capture.discard()).toBe(1);
    expect(await capture.waiting()).toBe(0);
  });

  it("réponse sans résultat ou incomplète : rupture de contrat", async () => {
    const { capture, deps } = setup();
    await queueSale(capture, "op-1");
    vi.mocked(deps.send).mockResolvedValueOnce({ results: [] });
    await expect(capture.syncNow("A")).rejects.toThrow(/sans résultat/);
    vi.mocked(deps.send).mockImplementationOnce((_s, body) =>
      Promise.resolve({ results: body.operations.map((op) => ({ ...accept(op), number: null })) }),
    );
    await expect(capture.syncNow("A")).rejects.toThrow(/définitif absent/);
    vi.mocked(deps.send).mockImplementationOnce((_s, body) =>
      Promise.resolve({
        results: body.operations.map((op) => ({ ...accept(op), status: "rejected" as const })),
      }),
    );
    await expect(capture.syncNow("A")).rejects.toThrow(/sans motif/);
  });

  it("watch : envoi à l'ouverture et au retour du réseau", async () => {
    const { capture, deps } = setup();
    await queueSale(capture, "op-1");
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.mocked(deps.fetchSnapshot).mockRejectedValueOnce(new Error("instantané cassé"));
    const stop = capture.watch("A", window);
    await vi.waitFor(() => {
      expect(error).toHaveBeenCalled();
    });
    window.dispatchEvent(new Event("online"));
    await vi.waitFor(() => {
      expect(deps.fetchSnapshot).toHaveBeenCalledTimes(2);
    });
    stop();
    expect(deps.send).toHaveBeenCalledTimes(1);
  });
});
