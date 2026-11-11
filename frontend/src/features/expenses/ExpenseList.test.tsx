import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { axeViolations } from "../../testing/axe";
import {
  ACCOUNTANT_ID,
  EXPENSES_PATH,
  expense,
  expenseRoutes,
  NOW,
  preloadExpenses,
  OWNER_ID,
  page,
  route,
  setClock,
} from "../../testing/expensesApi";
import { json } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { money, plain } from "../../testing/renderSale";

beforeAll(preloadExpenses);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

const ITEMS = [
  expense({ id: "e1", number: "D-000010", amount: 10000, category_id: "cat-carburant" }),
  expense({
    id: "e2",
    number: "D-000011",
    amount: 5000,
    category_id: "cat-repas",
    tags: [{ id: "t", name: "fête" }],
  }),
  expense({
    id: "e3",
    number: "D-000012",
    amount: 90000,
    category_id: "cat-loyer",
    status: "cancelled",
    editable: false,
    cancellation: {
      cancelled_at: "2026-11-11T09:32:00Z",
      cancelled_by: OWNER_ID,
      reason: "doublon",
    },
  }),
];

describe("Liste des dépenses (UC-DEP-03)", () => {
  it("liste du jour : total hors annulées, barres par catégorie, annulée barrée avec sa mention", async () => {
    const { container } = renderApp(EXPENSES_PATH, {
      ...expenseRoutes("owner"),
      [route("GET", "/expenses")]: json(200, page(ITEMS)),
    });
    const list = await screen.findByRole("list", { name: "Liste des dépenses" });
    expect(screen.getByText("Total — Dépenses du jour")).toBeVisible();
    expect(screen.getByText("15 000", { normalizer: plain })).toBeVisible();
    expect(screen.getByText("2 dépenses (annulées non comptées)")).toBeVisible();

    const bars = screen.getByRole("region", { name: "Par catégorie" });
    expect(within(bars).getByText(`${money(10000)} · 67 %`, { normalizer: plain })).toBeVisible();
    expect(within(bars).queryByText("Loyer")).toBeNull();

    const cancelled = within(list).getByText("D-000012").closest("a");
    if (cancelled === null) throw new Error("Ligne annulée introuvable");
    expect(within(cancelled).getByText("Annulée")).toBeVisible();
    expect(
      within(cancelled).getByText(
        "Annulée le 11/11/2026 à 10 h 32 par Awa Bello — motif : doublon",
        { normalizer: plain },
      ),
    ).not.toHaveClass("line-through");
    expect(within(cancelled).getByText(money(90000), { normalizer: plain })).toHaveClass(
      "line-through",
    );
    expect(within(list).getByText(/Paul Ndam · fête/)).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("filtres : période et catégorie envoyés au serveur", async () => {
    const { user, fake } = renderApp(EXPENSES_PATH, {
      ...expenseRoutes("owner"),
      [route("GET", "/expenses?from=2026-11-05&to=2026-11-11")]: json(
        200,
        page(ITEMS.slice(0, 1), { first_day: "2026-11-05" }),
      ),
      [route("GET", "/expenses?from=2026-11-05&to=2026-11-11&category_id=cat-carburant")]: json(
        200,
        page(ITEMS.slice(0, 1), { first_day: "2026-11-05" }),
      ),
    });
    await screen.findByText("Aucune dépense sur cette période.");
    await user.click(screen.getByRole("radio", { name: "7 derniers jours" }));
    expect(await screen.findByText("Total — Dépenses du 05/11/2026 au 11/11/2026")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Filtres" }));
    const category = screen.getByRole("radiogroup", { name: "Catégorie" });
    await user.click(within(category).getByRole("radio", { name: "Carburant" }));
    await screen.findByRole("list", { name: "Liste des dépenses" });
    expect(
      fake.count(route("GET", "/expenses?from=2026-11-05&to=2026-11-11&category_id=cat-carburant")),
    ).toBe(1);
  });

  it("comptable : filtre d'auteur « Moi », aucun nom des autres membres demandé", async () => {
    const { user, fake } = renderApp(EXPENSES_PATH, {
      ...expenseRoutes("accountant"),
      [route("GET", `/expenses?user_id=${ACCOUNTANT_ID}`)]: json(200, page([])),
    });
    await screen.findByText("Aucune dépense sur cette période.");
    expect(screen.queryByRole("button", { name: "Catégories et tags" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Filtres" }));
    await user.click(screen.getByRole("radio", { name: "Moi" }));
    await screen.findByText("Aucune dépense sur cette période.");
    expect(fake.count(route("GET", `/expenses?user_id=${ACCOUNTANT_ID}`))).toBe(1);
    expect(fake.count(route("GET", "/members"))).toBe(0);
  });

  it("« Voir plus » charge la page suivante", async () => {
    const { user } = renderApp(EXPENSES_PATH, {
      ...expenseRoutes("owner"),
      [route("GET", "/expenses")]: json(200, page(ITEMS.slice(0, 1), { next_cursor: "c2" })),
      [route("GET", "/expenses?cursor=c2")]: json(200, page(ITEMS.slice(1, 2))),
    });
    await screen.findByRole("list", { name: "Liste des dépenses" });
    await user.click(screen.getByRole("button", { name: "Voir plus" }));
    expect(await screen.findByText("D-000011")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Voir plus" })).toBeNull();
  });
});
