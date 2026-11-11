import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { formatMoney } from "../../shared/format";
import { axeViolations } from "../../testing/axe";
import {
  HOME,
  HOME_PATH,
  homeBody,
  homeRoutes,
  NOW,
  preloadDashboard,
} from "../../testing/dashboard";
import { setClock } from "../../testing/expensesApi";
import { SHOP_A } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { plain } from "../../testing/renderSale";
import { homeBlock } from "./useHome";

beforeAll(preloadDashboard);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

const money = (amount: number) => plain(formatMoney(amount));
const main = () => within(screen.getByRole("main"));
const day = async () => within(await screen.findByRole("list", { name: "Ma journée" }));
const noDashboardCall = (urls: string[]) => urls.every((url) => !url.includes("/dashboard"));

describe("accueils par rôle (UC-TDB-05)", () => {
  it("vendeur : « Nouvelle vente », « Versement », sa journée ; ni marge ni coût ; 360 px", async () => {
    const { user, router, fake, container } = renderApp(HOME_PATH, homeRoutes("seller"));
    const list = await day();
    expect(list.getByRole("button", { name: /Mes ventes du jour/ })).toHaveTextContent(
      `2 ventes${money(1_540_000)}`,
    );
    expect(list.getByText("1 client à relancer")).toBeVisible();
    expect(list.getByText("Aucune saisie en attente")).toBeVisible();
    expect(main().getByText(/Bonjour Awa Bello — Vendeur/)).toBeVisible();
    expect(screen.getByRole("main").textContent).not.toMatch(/marge|coût|CMP|bénéfice/i);
    expect(noDashboardCall(fake.calls.map((call) => call.url))).toBe(true);
    expect(container.innerHTML).not.toMatch(/overflow-x|w-max|min-w-max|w-screen/);
    expect(await axeViolations(container)).toEqual([]);

    await user.click(main().getByRole("button", { name: "Versement" }));
    expect(router.state.location.pathname).toBe(`/s/${SHOP_A}/creances`);
    expect(router.state.location.search).toBe("?vue=versement");
  });

  it("comptable : Achat, Dépense, Inventaire, « Déplacer du stock » au Lot 2 ; aucune vente", async () => {
    const { user, router, fake, container } = renderApp(HOME_PATH, homeRoutes("accountant"));
    const list = await day();
    expect(list.getByText("Disponible au Lot 2")).toBeVisible();
    expect(list.getByText("3 articles sous le seuil")).toBeVisible();
    expect(list.getByRole("button", { name: /Valeur du stock/ })).toHaveTextContent(
      money(12_500_000),
    );
    expect(list.getByRole("button", { name: /Dépenses du jour/ })).toHaveTextContent(money(45_000));
    const move = main().getByRole("button", { name: "Déplacer du stock" });
    expect(move).toHaveAttribute("aria-disabled", "true");
    expect(move).toHaveAccessibleDescription("Disponible au Lot 2");
    expect(screen.getByRole("main").textContent).not.toMatch(/vente|chiffre d'affaires|marge/i);
    expect(noDashboardCall(fake.calls.map((call) => call.url))).toBe(true);
    expect(await axeViolations(container)).toEqual([]);

    await user.click(main().getByRole("button", { name: "Achat" }));
    expect(`${router.state.location.pathname}${router.state.location.search}`).toBe(
      `/s/${SHOP_A}/achats?vue=nouvel`,
    );
  });

  it.each([
    ["Dépense", `/s/${SHOP_A}/depenses?vue=nouvelle`],
    ["Inventaire", `/s/${SHOP_A}/stock?vue=inventaire`],
  ])("comptable : « %s » ouvre son écran", async (label, path) => {
    const { user, router } = renderApp(HOME_PATH, homeRoutes("accountant"));
    await day();
    await user.click(main().getByRole("button", { name: label }));
    expect(`${router.state.location.pathname}${router.state.location.search}`).toBe(path);
  });

  it("chauffeur : accueil « Disponible au Lot 2 », sans faux zéro", async () => {
    const { container } = renderApp(HOME_PATH, homeRoutes("driver"));
    const list = within(await screen.findByRole("list", { name: "Mon voyage" }));
    expect(list.getAllByText("Disponible au Lot 2")).toHaveLength(2);
    expect(screen.getByRole("main").textContent).not.toMatch(/0 FCFA/);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("vendeur hors connexion : les boutons restent, les chiffres sont remplacés", async () => {
    renderApp(HOME_PATH, homeRoutes("seller", { [HOME]: new TypeError("Failed to fetch") }));
    expect(await screen.findByText("Chiffres disponibles avec internet")).toBeVisible();
    expect(main().getByRole("button", { name: "Nouvelle vente" })).toBeVisible();
    expect(screen.queryByRole("list", { name: "Ma journée" })).toBeNull();
  });

  it("le bloc d'un autre rôle, ou un bloc absent, est refusé (fail-fast)", () => {
    expect(() => homeBlock(homeBody("seller"), "accountant")).toThrow(
      "Accueil « seller » reçu pour « accountant »",
    );
    expect(() => homeBlock({ role: "driver", today: "2026-11-11" }, "driver")).toThrow(
      "Accueil « driver » sans son bloc",
    );
    expect(homeBlock(homeBody("driver"), "driver").current_trip.lot).toBe(2);
  });
});
