import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { formatMoney } from "../../shared/format";
import { axeViolations } from "../../testing/axe";
import { HOME_PATH, homeBody, homeRoutes, NOW, preloadDashboard } from "../../testing/dashboard";
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

describe("accueils du comptable et du chauffeur (UC-TDB-05)", () => {
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

  it.each(["accountant", "driver"] as const)(
    "%s : pas de bouton de vente, pas de « Mon compte » dans la page (il est dans la barre du haut)",
    async (role) => {
      renderApp(HOME_PATH, homeRoutes(role));
      await screen.findByText(/Bonjour Awa Bello/);
      expect(main().queryByRole("button", { name: "Nouvelle vente" })).toBeNull();
      expect(main().queryByRole("button", { name: "Mon compte" })).toBeNull();
      const bar = within(screen.getByRole("banner"));
      expect(bar.getByRole("button", { name: "Mon compte" })).toBeVisible();
    },
  );

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
