import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { SaleResult } from "../../core/gateways/salesContract";
import { formatTime } from "../../shared/format";
import { axeViolations } from "../../testing/axe";
import {
  DASHBOARD_TODAY,
  dashboardBody,
  HOME_PATH,
  modulesProfile,
  NOW,
  PRICE_REQUESTS,
  preloadDashboard,
  PROFILE,
} from "../../testing/dashboard";
import { setClock } from "../../testing/expensesApi";
import { json, SHOP_A } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { money, plain } from "../../testing/renderSale";
import { cancelled, page, saleCommand } from "../../testing/salesFixtures";
import { addSale, API, saleServer, type Routes, type SaleRole } from "../../testing/salesServer";

beforeAll(preloadDashboard);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

const S = `/s/${SHOP_A}`;
const SALES = `GET ${API}/sales`;
const CUSTOMERS = `GET ${API}/customers`;
const MOUSSA = { id: "cus-moussa", name: "Moussa Abdou", phone: "+237690000000" };
const customer = { ...MOUSSA, kind: "individual", city: null, address: null };
const customerBody = {
  ...customer,
  id_doc_type: null,
  id_doc_number: null,
  id_doc_photo_id: null,
  credit_limit: null,
  note: null,
  created_by: "u",
  version: 1,
};

/** Une vente réelle du faux serveur, recopiée `count` fois (V-000201…, crédit une sur deux). */
async function salesOf(role: SaleRole, count: number): Promise<SaleResult[]> {
  const server = saleServer(role);
  const credit = await addSale(
    server,
    saleCommand({
      kind: "credit",
      customer: { ...MOUSSA, kind: "individual" },
      payments: [{ mode_id: "pm-orange", amount: 200_000, reference: null }],
    }),
  );
  const cash: SaleResult = { ...credit, kind: "cash", customer_id: null, credit: null };
  return Array.from({ length: count }, (_, i) => ({
    ...(i % 2 === 0 ? cash : credit),
    id: `sale-${String(201 + i)}`,
    number: `V-000${String(201 + i)}`,
  }));
}

/** Accueil du rôle : ventes du jour `items` (plus récentes en haut), clients, routes `more`. */
function openHome(role: SaleRole, items: SaleResult[], more: Routes = {}) {
  const server = saleServer(role);
  Object.assign(server.routes, {
    [SALES]: json(200, page(items)),
    [CUSTOMERS]: json(200, { items: [customerBody] }),
    ...more,
  });
  return renderApp(HOME_PATH, server.routes);
}

const main = () => within(screen.getByRole("main"));
const recent = () => screen.findByRole("list", { name: "Dernières ventes" });

describe("page d'accueil minimale (specs § 15.1)", () => {
  it("vendeur : « Nouvelle vente », son total, ses 5 dernières ventes ; ni coût ni marge", async () => {
    const six = await salesOf("seller", 6);
    const { user, router, fake, container } = openHome("seller", six);
    const rows = within(await recent()).getAllByRole("listitem");
    expect(rows).toHaveLength(5);
    const [first] = rows;
    if (first === undefined) throw new Error("Aucune ligne");
    const time = plain(formatTime(six[0]?.sold_at ?? ""));
    expect(plain(first.textContent)).toBe(`V-000206Moussa Abdou · ${time}${money(780_000)}Crédit`);
    expect(plain(rows[1]?.textContent ?? "")).toContain("Comptant");
    expect(screen.getByRole("heading", { name: "5 dernières ventes" })).toBeVisible();
    const total = screen.getByRole("button", { name: /^Ventes du jour/ });
    expect(total).toHaveTextContent(plain(`6 ventes`));
    expect(screen.getByRole("main").textContent).not.toMatch(/marge|coût|CMP|bénéfice/i);
    const urls = fake.calls.map((call) => call.url);
    expect(urls.some((url) => /\/(dashboard|home|profile)\b/.test(url))).toBe(false);
    expect(await axeViolations(container)).toEqual([]);

    await user.click(first.querySelector("button") ?? first);
    expect(`${router.state.location.pathname}${router.state.location.search}`).toBe(
      `${S}/mes-ventes?id=sale-206`,
    );
  });

  it("le grand bouton « Nouvelle vente » ouvre la vente ; le total du vendeur ouvre « Mes ventes »", async () => {
    const { user, router } = openHome("seller", []);
    await user.click(await screen.findByRole("button", { name: /^Ventes du jour/ }));
    expect(router.state.location.pathname).toBe(`${S}/mes-ventes`);
    await router.navigate(HOME_PATH);
    await user.click(await main().findByRole("button", { name: "Nouvelle vente" }));
    expect(router.state.location.pathname).toBe(`${S}/nouvelle-vente`);
  });

  it("aucune vente : « Aucune vente aujourd'hui », total à zéro", async () => {
    openHome("seller", []);
    expect(await screen.findByText("Aucune vente aujourd'hui")).toBeVisible();
    expect(screen.getByRole("button", { name: /^Ventes du jour/ })).toHaveTextContent(
      "Aucune vente",
    );
  });

  it("hors connexion : « Connexion nécessaire » et « Réessayer », sans chiffre", async () => {
    const items = await salesOf("seller", 2);
    const { user, fake } = openHome("seller", items, { [SALES]: new TypeError("Failed to fetch") });
    expect(
      await screen.findByText("Connexion nécessaire pour afficher les ventes du jour."),
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: /^Ventes du jour/ })).toBeNull();
    expect(screen.queryByRole("list", { name: "Dernières ventes" })).toBeNull();
    expect(main().getByRole("button", { name: "Nouvelle vente" })).toBeVisible();
    const before = fake.count(SALES);
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    await vi.waitFor(() => {
      expect(fake.count(SALES)).toBeGreaterThan(before);
    });
  });

  it("vente annulée : barrée, pastille « Annulée »", async () => {
    const [only] = await salesOf("owner", 1);
    if (only === undefined) throw new Error("Aucune vente");
    openHome("owner", [cancelled(only, "Erreur")], { [PROFILE]: modulesProfile() });
    const row = within(await recent()).getByRole("listitem");
    expect(within(row).getByText("Annulée")).toBeVisible();
  });
});

describe("propriétaire : accès au tableau de bord complet (module `dashboard`)", () => {
  const dashboard = {
    [DASHBOARD_TODAY]: json(200, dashboardBody()),
    [PRICE_REQUESTS]: json(200, []),
  };

  it("module actif : « Ventes du jour » et « Plus → Tableau de bord » l'ouvrent", async () => {
    const items = await salesOf("owner", 3);
    const more = { [PROFILE]: modulesProfile(), ...dashboard };
    const { user, router } = openHome("owner", items, more);
    expect(within(await recent()).getAllByRole("listitem")).toHaveLength(3);
    expect(screen.getByRole("main").textContent).not.toMatch(/marge/i);
    await user.click(screen.getByRole("button", { name: /^Ventes du jour/ }));
    expect(router.state.location.pathname).toBe(`${S}/tableau-de-bord`);
    expect(await screen.findByRole("heading", { name: "Tableau de bord" })).toBeVisible();
    expect(await screen.findByRole("radiogroup", { name: "Période" })).toBeVisible();

    await user.click(screen.getByRole("link", { name: "Plus" }));
    await user.click(await screen.findByRole("button", { name: "Tableau de bord" }));
    expect(router.state.location.pathname).toBe(`${S}/tableau-de-bord`);
  });

  it("module inactif : ni tuile ni accès ; le total ouvre « Ventes » ; l'adresse est introuvable", async () => {
    const items = await salesOf("owner", 1);
    const more = { [PROFILE]: modulesProfile(["core", "sales"]) };
    const { user, router, fake } = openHome("owner", items, more);
    await recent();
    await user.click(screen.getByRole("button", { name: /^Ventes du jour/ }));
    expect(router.state.location.pathname).toBe(`${S}/ventes`);

    await user.click(screen.getByRole("link", { name: "Plus" }));
    await screen.findByRole("button", { name: "Réglages" });
    await vi.waitFor(() => {
      expect(fake.count(PROFILE)).toBeGreaterThanOrEqual(2);
    });
    expect(screen.queryByRole("button", { name: "Tableau de bord" })).toBeNull();

    await router.navigate(`${S}/tableau-de-bord`);
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
    expect(fake.count(DASHBOARD_TODAY)).toBe(0);
  });
});
