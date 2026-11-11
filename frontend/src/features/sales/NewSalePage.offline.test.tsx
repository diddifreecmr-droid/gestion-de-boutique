/**
 * Vente sans réseau (UC-VEN-10, recette OFF-01, OFF-04, OFF-07) dans l'application complète.
 * - Droit `offline_capture` inactif (V1) : « Connexion nécessaire », Dexie jamais chargé,
 *   aucune requête `/sync` ni `/offline-snapshot`, rien d'écrit sur l'appareil.
 * - Droit actif (configuration de test) : reçu provisoire `V-HL-…`, compteur « 1 saisie en
 *   attente d'envoi », envoi au retour du réseau, message « Vente V-HL-… → V-000124 ».
 */
import "fake-indexeddb/auto";
import { screen } from "@testing-library/react";
import { Dexie } from "dexie";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { DB_NAME } from "../../core/offline/db";
import { RIGHTS_KEY } from "../../core/offline/rights";
import { json, type Call } from "../../testing/fakeApi";
import {
  articleButton,
  preloadSales,
  renderSale,
  saleAlert,
  validateButton,
} from "../../testing/renderSale";
import { saleProfile } from "../../testing/salesCatalog";
import { API } from "../../testing/salesServer";
import { OFFLINE_MESSAGE } from "./saleErrorMessage";

const engineLoads = vi.hoisted(() => ({ count: 0 }));
vi.mock("../../core/offline/engine", async (original) => {
  engineLoads.count += 1;
  return original();
});

beforeAll(preloadSales);
afterEach(async () => {
  window.localStorage.clear();
  engineLoads.count = 0;
  await Dexie.delete(DB_NAME);
});

const SNAPSHOT = {
  generated_at: "2026-11-11T10:00:00Z",
  since: null,
  full: true,
  min_price_enabled: true,
  articles: [
    { id: "art-hj125-8", display_name: "Haojue HJ125-8", reference: null, stock_unit: "unit",
      sold_by_piece: false, base_price: 780_000, base_price_piece: null, min_price: 720_000,
      min_price_piece: null },
  ],
  customers: [], expense_categories: [], locations: [], payment_modes: [],
}; // prettier-ignore

describe("droit inactif (V1) : comportement inchangé", () => {
  it("coupure : « Connexion nécessaire », aucune file, aucun appel à /sync", async () => {
    const { user, network, fake } = renderSale();
    await user.click(await articleButton("Haojue HJ125-8"));
    network.online = false;
    await user.click(validateButton());
    expect(await saleAlert()).toHaveTextContent(OFFLINE_MESSAGE);
    expect(screen.queryByText(/en attente d'envoi/)).toBeNull();
    expect(engineLoads.count).toBe(0);
    expect(fake.calls.some((c) => /\/sync|offline-snapshot/.test(c.url))).toBe(false);
    expect(window.localStorage.getItem(RIGHTS_KEY)).toBeNull();
  });
});

describe("droit actif (configuration de test)", () => {
  it("vente hors ligne → reçu provisoire → envoi au retour du réseau → numéro définitif", async () => {
    const net = { online: true };
    const offline = () => new TypeError("Failed to fetch");
    const sync = (call: Call) => {
      if (!net.online) throw offline();
      const body = call.body as { operations: { op_id: string; provisional_number: string }[] };
      return json(200, {
        results: body.operations.map((op) => ({
          op_id: op.op_id, status: "accepted", provisional_number: op.provisional_number,
          number: "V-000124", entity_id: op.op_id, warnings: [], error: null,
        })),
      }); // prettier-ignore
    };
    const { user, network, fake } = renderSale("seller", {
      extra: {
        [`GET ${API}/profile`]: json(200, {
          ...saleProfile("seller"),
          entitlements: { offline_capture: true },
        }),
        [`GET ${API}/offline-snapshot`]: () => (net.online ? json(200, SNAPSHOT) : Promise.reject(offline())),
        [`POST ${API}/sync`]: sync,
      },
    }); // prettier-ignore
    await user.click(await articleButton("Haojue HJ125-8"));
    await vi.waitFor(() => {
      expect(fake.count(`GET ${API}/offline-snapshot`)).toBe(1);
    });
    network.online = false;
    net.online = false;
    await user.click(validateButton());
    const heading = await screen.findByRole("heading", { name: /reçu n° V-HL-[0-9A-F]{4}-0001/ });
    const provisional = /V-HL-[0-9A-F]{4}-0001/.exec(heading.textContent)?.[0] ?? "";
    expect(await screen.findByText("1 saisie en attente d'envoi")).toBeVisible();
    expect(screen.getByText(/la saisie partira au retour du réseau/)).toBeVisible();
    expect(fake.count(`POST ${API}/sales`)).toBe(1); // tenté une fois, puis mis en file

    network.online = true;
    net.online = true;
    window.dispatchEvent(new Event("online"));
    expect(await screen.findByText(`Vente ${provisional} → V-000124`)).toBeVisible();
    expect(screen.queryByText(/en attente d'envoi/)).toBeNull();
    const sent = fake.calls.find((c) => c.method === "POST" && c.url.endsWith("/sync"));
    expect(sent?.body).toMatchObject({
      operations: [{ type: "sale.create", provisional_number: provisional }],
    });
    expect(engineLoads.count).toBe(1);
  });
});
