import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { formatMoney } from "../../shared/format";
import { axeViolations } from "../../testing/axe";
import {
  detailBody,
  detailRoute,
  HOME_PATH,
  homeRoutes,
  NOW,
  preloadDashboard,
  weekBody,
} from "../../testing/dashboard";
import { setClock } from "../../testing/expensesApi";
import { json, SHOP_A } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { plain } from "../../testing/renderSale";

beforeAll(preloadDashboard);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

const money = (amount: number) => plain(formatMoney(amount));
const day = "2026-11-11";

const SALES = detailBody(
  "sales",
  [
    { kind: "sale", id: "sale-124", label: "V-000124", day, amount: 1_540_000, margin: 410_000 },
    { kind: "sale", id: "sale-125", label: "V-000125", day, amount: 800_000, margin: null },
    {
      kind: "cancellation",
      id: "sale-120",
      label: "V-000120",
      day,
      amount: -50_000,
      margin: -5_000,
    },
    { kind: "return", id: "ret-1", label: "V-000110", day, amount: -20_000, margin: -2_000 },
  ],
  2_270_000,
);
const PAYMENTS = detailBody(
  "payments",
  [
    { kind: "payment_mode", id: "mode-cash", label: "Espèces", amount: 900_000, count: 3 },
    { kind: "payment_mode", id: "mode-om", label: "Orange Money", amount: -10_000, count: -1 },
  ],
  890_000,
);
const LOW = detailBody(
  "low_stock",
  [{ kind: "article", id: "art-1", label: "Haojue HJ125-8", quantity: "1", threshold: "3" }],
  1,
);

describe("détail d'un chiffre (UC-TDB-04)", () => {
  it("« Ventes du jour » : la liste qui l'explique, fiche d'une vente, retour à l'accueil", async () => {
    const { user, router, container } = renderApp(
      HOME_PATH,
      homeRoutes("owner", { [detailRoute("sales")]: json(200, SALES) }),
    );
    await user.click(await screen.findByRole("button", { name: /^Ventes du jour/ }));
    expect(router.state.location.search).toBe("?detail=sales");
    expect(await screen.findByRole("heading", { name: "Ventes de la période" })).toBeVisible();
    expect(screen.queryByText(/Bonjour/)).toBeNull();
    expect(screen.getByText("Le 11/11/2026")).toBeVisible();
    expect(screen.getByText(money(2_270_000))).toBeVisible();
    const rows = within(screen.getByRole("list", { name: "Ventes de la période" }))
      .getAllByRole("listitem")
      .map((item) => plain(item.textContent));
    expect(rows).toEqual([
      `Vente V-00012411/11/2026 · Marge : ${money(410_000)}${money(1_540_000)}`,
      `Vente V-00012511/11/2026 · Marge non calculable (coût inconnu)${money(800_000)}`,
      `Annulation de la vente V-00012011/11/2026 · Marge : ${money(-5_000)}${money(-50_000)}`,
      `Retour sur la vente V-00011011/11/2026 · Marge : ${money(-2_000)}${money(-20_000)}`,
    ]);
    expect(screen.queryByRole("button", { name: /Retour sur la vente/ })).toBeNull();
    expect(await axeViolations(container)).toEqual([]);

    await user.click(screen.getByRole("button", { name: "Retour à l'accueil" }));
    expect(router.state.location.search).toBe("");
    expect(await screen.findByRole("button", { name: /^Ventes du jour/ })).toBeVisible();

    await user.click(screen.getByRole("button", { name: /^Ventes du jour/ }));
    await user.click(await screen.findByRole("button", { name: /^Vente V-000124/ }));
    expect(router.state.location.pathname).toBe(`/s/${SHOP_A}/ventes`);
    expect(router.state.location.search).toBe("?id=sale-124");
  });

  it("argent encaissé : par mode de paiement, sur la période choisie", async () => {
    const week = "period=week";
    const { user, fake } = renderApp(
      `${HOME_PATH}?periode=week`,
      homeRoutes("owner", {
        [`GET /api/v1/shops/${SHOP_A}/dashboard?${week}`]: json(200, weekBody()),
        [detailRoute("payments", week)]: json(200, PAYMENTS),
      }),
    );
    await user.click(await screen.findByRole("button", { name: /^Argent encaissé de la semaine/ }));
    const list = within(
      await screen.findByRole("list", { name: "Argent encaissé par mode de paiement" }),
    );
    expect(list.getAllByRole("listitem").map((item) => plain(item.textContent))).toEqual([
      `Espèces3 paiements${money(900_000)}`,
      `Orange Money1 annulation${money(-10_000)}`,
    ]);
    expect(fake.count(detailRoute("payments", week))).toBe(1);
  });

  it("stock bas : articles sous le seuil, total en nombre d'articles", async () => {
    const { user } = renderApp(
      HOME_PATH,
      homeRoutes("owner", { [detailRoute("low_stock")]: json(200, LOW) }),
    );
    await user.click(await screen.findByRole("button", { name: /^Stock bas/ }));
    expect(await screen.findByText("1 article sous le seuil")).toBeVisible();
    expect(screen.getByText("Stock : 1 · seuil : 3")).toBeVisible();
  });

  it("liste vide et hors connexion", async () => {
    const { user } = renderApp(`${HOME_PATH}?detail=expenses`, {
      ...homeRoutes("owner"),
      [detailRoute("expenses")]: [
        new TypeError("Failed to fetch"),
        new TypeError("Failed to fetch"),
        json(200, detailBody("expenses", [], 0)),
      ],
    });
    expect(await screen.findByText("Chiffres disponibles avec internet")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByText("Rien à afficher sur cette période.")).toBeVisible();
  });
});
