import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { formatMoney, NBSP } from "../../../shared/format";
import { axeViolations } from "../../../testing/axe";
import { DASHBOARD_PATH, homeRoutes, NOW, preloadDashboard } from "../../../testing/dashboard";
import { sectionToggle } from "../../../testing/dashboardFold";
import { setClock } from "../../../testing/expensesApi";
import { renderApp } from "../../../testing/renderApp";
import { plain } from "../../../testing/renderSale";

beforeAll(async () => {
  await preloadDashboard();
  await import("./MarginsWide");
});
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

/** Grand écran (≥ 1024 px) : `matchMedia` répond vrai. */
function wideScreen(): void {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: true,
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  }));
}

async function openMargins() {
  const rendered = renderApp(DASHBOARD_PATH, homeRoutes("owner"));
  await rendered.user.click(await sectionToggle("Coûts et marges"));
  return rendered;
}

describe("Coûts et marges du propriétaire (specs § 15.1, design-system § 7.2)", () => {
  it("téléphone : marge, taux et 3 meilleurs articles, sans tableau ni graphique ; axe", async () => {
    const { container } = await openMargins();
    const term = await screen.findByText("Marge totale");
    const totals = within(term.closest("dl") as HTMLElement);
    expect(totals.getByText(plain(formatMoney(305_000)))).toBeVisible();
    expect(totals.getByText(plain(`30,81${NBSP}%`))).toBeVisible();
    expect(screen.getByText("1 ligne sans coût d'achat, hors marge")).toBeVisible();
    const best = within(screen.getByRole("list", { name: "Articles qui rapportent le plus" }));
    expect(best.getAllByRole("listitem").map((item) => plain(item.textContent))).toEqual([
      plain(`1. Haojue DR160${formatMoney(250_000)}`),
      plain(`2. Djampar — Rouge${formatMoney(30_000)}`),
      plain(`3. Djampar — Vert${formatMoney(20_000)}`),
    ]);
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.queryByRole("img")).toBeNull();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("grand écran : tableaux triables (au mètre, au rouleau), historique et graphique ; axe", async () => {
    wideScreen();
    const { container, user } = await openMargins();
    const articles = await screen.findByRole("table", { name: "Par article" });
    const headers = within(articles).getAllByRole("columnheader");
    expect(headers.map((h) => h.textContent)).toContain("Marge au rouleau");
    expect(headers.find((h) => h.textContent === "Marge")).toHaveAttribute(
      "aria-sort",
      "descending",
    );
    const names = () =>
      within(articles)
        .getAllByRole("row")
        .slice(1)
        .map((row) => row.firstChild?.textContent);
    expect(names()[0]).toBe("Haojue DR160");
    await user.click(within(articles).getByRole("button", { name: "Article" }));
    expect(names()).toEqual([
      "Haojue DR160",
      "Djampar — Vert",
      "Djampar — Rouge",
      "Djampar — Bleu",
    ]);
    await user.click(within(articles).getByRole("button", { name: "Article" }));
    expect(names()[0]).toBe("Djampar — Bleu");
    const fabrics = screen.getByRole("table", { name: "Par tissu (toutes couleurs)" });
    expect(within(fabrics).getByRole("row", { name: /Djampar/ })).toHaveTextContent(
      plain(formatMoney(30_556)),
    );
    const history = screen.getByRole("table", { name: "Historique des derniers jours" });
    expect(within(history).getAllByRole("row")).toHaveLength(3);
    expect(screen.getByRole("img", { name: /^Ventes et marge par jour/ })).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
  });
});
