import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import {
  EXPENSES_PATH,
  expenseRoutes,
  NOW,
  preloadExpenses,
  setClock,
} from "../../testing/expensesApi";
import { SHOP_A } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";

beforeAll(preloadExpenses);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

const nav = () => screen.getByRole("navigation", { name: "Navigation principale" });

describe("emplacement des Dépenses (CDC § 17.4) et droits par rôle (§ 4.2)", () => {
  it("comptable : entrée « Dépenses » de la barre du bas", async () => {
    const { user, router } = renderApp(`/s/${SHOP_A}`, expenseRoutes("accountant"));
    await user.click(
      await within(
        await screen.findByRole("navigation", { name: "Navigation principale" }),
      ).findByRole("link", { name: "Dépenses" }),
    );
    expect(router.state.location.pathname).toBe(EXPENSES_PATH);
    expect(await screen.findByRole("button", { name: "Nouvelle dépense" })).toBeVisible();
    expect(within(nav()).getByRole("link", { name: "Dépenses" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("propriétaire : « Plus » → « Dépenses »", async () => {
    const { user, router } = renderApp(`/s/${SHOP_A}/plus`, expenseRoutes("owner"));
    await user.click(await screen.findByRole("button", { name: "Dépenses" }));
    expect(router.state.location.pathname).toBe(EXPENSES_PATH);
    expect(await screen.findByRole("button", { name: "Catégories et tags" })).toBeVisible();
    expect(within(nav()).getByRole("link", { name: "Plus" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it.each(["seller", "driver"] as const)(
    "%s : aucune entrée, « Page introuvable » par l'adresse",
    async (role) => {
      const { fake } = renderApp(EXPENSES_PATH, expenseRoutes(role));
      expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
      // Le chauffeur n'a pas de barre du bas (menu servi vide) : aucun lien nulle part.
      expect(screen.queryByRole("link", { name: "Dépenses" })).toBeNull();
      expect(fake.calls.some((call) => call.url.includes("/expense"))).toBe(false);
    },
  );

  it("comptable : les réglages des catégories n'existent pas pour lui", async () => {
    renderApp(`${EXPENSES_PATH}?vue=reglages`, expenseRoutes("accountant"));
    expect(await screen.findByText("Aucune dépense sur cette période.")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Catégories et tags" })).toBeNull();
  });
});
