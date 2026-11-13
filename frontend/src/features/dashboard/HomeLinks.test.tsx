import { screen } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { DASHBOARD_PATH, homeRoutes, NOW, preloadDashboard } from "../../testing/dashboard";
import { unfoldSections } from "../../testing/dashboardFold";
import { setClock } from "../../testing/expensesApi";
import { SHOP_A } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";

beforeAll(preloadDashboard);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

const S = `/s/${SHOP_A}`;
const D = DASHBOARD_PATH;

/** Chaque chiffre s'ouvre d'un appui (UC-TDB-04) : sa liste, ou l'écran qui le gère. */
describe("accès depuis le tableau de bord et les accueils", () => {
  it.each([
    [/^Argent encaissé du jour/, `${D}?detail=payments`],
    [/^Marge du jour/, `${D}?detail=sales`],
    [/^Dépenses du jour/, `${D}?detail=expenses`],
    [/^1 vente sans coût connu/, `${D}?detail=sales`],
    [/^Total à recevoir/, `${D}?detail=receivables`],
    [/^Versements reçus du jour/, `${D}?detail=payments`],
    [/^Rappels du jour/, `${S}/creances`],
    [/^Valeur du stock/, `${S}/stock?vue=valeur`],
    [/^Stock abîmé/, `${S}/stock?vue=abime`],
    [/^Stock bas/, `${D}?detail=low_stock`],
    [/^Stock à vérifier/, `${S}/stock`],
    [/^Erreurs signalées/, `${S}/ventes`],
  ])("propriétaire : %s → %s", async (name, target) => {
    const { user, router } = renderApp(DASHBOARD_PATH, homeRoutes("owner"));
    await screen.findByText("2 erreurs à traiter");
    await unfoldSections(user);
    await user.click(await screen.findByRole("button", { name }));
    expect(`${router.state.location.pathname}${router.state.location.search}`).toBe(target);
  });

  it.each([
    ["accountant", /^Alertes de stock/, `${S}/stock`],
    ["accountant", /^Valeur du stock/, `${S}/stock?vue=valeur`],
    ["accountant", /^Dépenses du jour/, `${S}/depenses`],
  ] as const)("%s : %s → %s", async (role, name, target) => {
    const { user, router } = renderApp(S, homeRoutes(role));
    await user.click(await screen.findByRole("button", { name }));
    expect(`${router.state.location.pathname}${router.state.location.search}`).toBe(target);
  });
});
