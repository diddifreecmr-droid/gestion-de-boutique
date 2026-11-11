import { screen } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { HOME_PATH, homeRoutes, NOW, preloadDashboard } from "../../testing/dashboard";
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

/** Chaque chiffre s'ouvre d'un appui (UC-TDB-04) : sa liste, ou l'écran qui le gère. */
describe("accès depuis les accueils", () => {
  it.each([
    [/^Argent encaissé du jour/, `${S}?detail=payments`],
    [/^Marge du jour/, `${S}?detail=sales`],
    [/^Dépenses du jour/, `${S}?detail=expenses`],
    [/^1 vente sans coût connu/, `${S}?detail=sales`],
    [/^Total à recevoir/, `${S}?detail=receivables`],
    [/^Versements reçus du jour/, `${S}?detail=payments`],
    [/^Rappels du jour/, `${S}/creances`],
    [/^Valeur du stock/, `${S}/stock?vue=valeur`],
    [/^Stock abîmé/, `${S}/stock?vue=abime`],
    [/^Stock bas/, `${S}?detail=low_stock`],
    [/^Stock à vérifier/, `${S}/stock`],
    [/^Erreurs signalées/, `${S}/ventes`],
  ])("propriétaire : %s → %s", async (name, target) => {
    const { user, router } = renderApp(HOME_PATH, homeRoutes("owner"));
    await screen.findByText("2 erreurs à traiter");
    await user.click(await screen.findByRole("button", { name }));
    expect(`${router.state.location.pathname}${router.state.location.search}`).toBe(target);
  });

  it.each([
    ["seller", /^Mes ventes du jour/, `${S}/mes-ventes`],
    ["seller", /^Mes rappels du jour/, `${S}/creances`],
    ["seller", /^Nouvelle vente/, `${S}/nouvelle-vente`],
    ["accountant", /^Alertes de stock/, `${S}/stock`],
    ["accountant", /^Valeur du stock/, `${S}/stock?vue=valeur`],
    ["accountant", /^Dépenses du jour/, `${S}/depenses`],
  ] as const)("%s : %s → %s", async (role, name, target) => {
    const { user, router } = renderApp(HOME_PATH, homeRoutes(role));
    await user.click(await screen.findByRole("button", { name }));
    expect(`${router.state.location.pathname}${router.state.location.search}`).toBe(target);
  });
});
