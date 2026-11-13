import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { SHOP_A } from "../../testing/fakeApi";
import {
  NOW,
  preloadPurchasing,
  PURCHASES_PATH,
  purchasingRoutes,
  setClock,
} from "../../testing/purchasing";
import { renderApp } from "../../testing/renderApp";

beforeAll(preloadPurchasing);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

const nav = () => screen.getByRole("navigation", { name: "Navigation principale" });

describe("emplacement des Achats (CDC § 17.4) et droits par rôle (§ 4.2)", () => {
  it("comptable : entrée « Achats » de la barre du bas ; réglages non lus", async () => {
    const { user, router, fake } = renderApp(`/s/${SHOP_A}`, purchasingRoutes("accountant"));
    const bar = await screen.findByRole("navigation", { name: "Navigation principale" });
    await user.click(within(bar).getByRole("link", { name: "Achats" }));
    expect(router.state.location.pathname).toBe(PURCHASES_PATH);
    expect(await screen.findByRole("button", { name: "Nouvel achat" })).toBeVisible();
    expect(within(nav()).getByRole("link", { name: "Achats" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(fake.calls.some((call) => call.url.endsWith("/settings"))).toBe(false);
  });

  it("propriétaire : « Plus » → « Achats »", async () => {
    const { user, router } = renderApp(`/s/${SHOP_A}/plus`, purchasingRoutes("owner"));
    await user.click(await screen.findByRole("button", { name: "Achats" }));
    expect(router.state.location.pathname).toBe(PURCHASES_PATH);
    expect(await screen.findByRole("heading", { name: "Achats" })).toBeVisible();
    expect(within(nav()).getByRole("link", { name: "Plus" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it.each(["seller", "driver"] as const)(
    "%s : aucune entrée, « Page introuvable » par l'adresse, aucun appel",
    async (role) => {
      const { fake } = renderApp(`${PURCHASES_PATH}?vue=nouvel`, purchasingRoutes(role));
      expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
      // Le chauffeur n'a pas de barre du bas (menu servi vide) : aucun lien nulle part.
      expect(screen.queryByRole("link", { name: "Achats" })).toBeNull();
      const touched = fake.calls.some((c) => /\/(purchases|suppliers)/.test(c.url));
      expect(touched).toBe(false);
    },
  );

  it("connexion absente à l'ouverture : « Réessayer » relit les référentiels", async () => {
    const routes = purchasingRoutes("accountant");
    const key = Object.keys(routes).find((k) => k.endsWith("/suppliers"));
    if (key === undefined) throw new Error("route des fournisseurs absente");
    const ok = routes[key];
    if (ok === undefined || Array.isArray(ok)) throw new Error("réponse inattendue");
    routes[key] = [new TypeError("Failed to fetch"), ok];
    const { user } = renderApp(PURCHASES_PATH, routes);
    expect(await screen.findByText("Connexion nécessaire pour ouvrir les achats.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("button", { name: "Nouvel achat" })).toBeVisible();
  });
});
