/**
 * Tableau de bord au premier coup d'œil (audit UX du 13/11/2026, téléphone 360 × 800) : la
 * période, puis les 3 chiffres (ventes, argent encaissé, marge) ; dépenses et résultat, jour par
 * jour, créances, stock et camions repliés à un appui ; les alertes restent ouvertes.
 */
import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { formatMoney } from "../../shared/format";
import { axeViolations } from "../../testing/axe";
import { DASHBOARD_PATH, homeRoutes, NOW, preloadDashboard } from "../../testing/dashboard";
import { sectionToggle } from "../../testing/dashboardFold";
import { setClock } from "../../testing/expensesApi";
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

const FOLDED = ["Dépenses et résultat", "Créances", "Stock", "Camions"];

describe("tableau de bord — l'essentiel au premier coup d'œil", () => {
  it("3 chiffres en haut, le reste replié derrière son titre ; alertes ouvertes ; axe", async () => {
    const { container } = renderApp(DASHBOARD_PATH, homeRoutes("owner"));
    const key = await screen.findByRole("region", { name: "Chiffres clés" });
    expect(
      within(key)
        .getAllByRole("button")
        .slice(0, 3)
        .map((button) => button.textContent.split(/\d/)[0]),
    ).toEqual(["Ventes du jour", "Argent encaissé du jour", "Marge du jour"]);
    for (const title of FOLDED) {
      expect(await sectionToggle(title)).toHaveAttribute("aria-expanded", "false");
    }
    expect(screen.queryByRole("list", { name: "Stock" })).toBeNull();
    expect(screen.queryByRole("list", { name: "Créances" })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Dépenses du jour/ })).toBeNull();
    expect(await sectionToggle("Alertes en attente")).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("2 erreurs à traiter")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("« Dépenses et résultat » : résumé des deux montants, puis le détail d'un appui", async () => {
    const { user } = renderApp(DASHBOARD_PATH, homeRoutes("owner"));
    const toggle = await sectionToggle("Dépenses et résultat");
    expect(toggle).toHaveTextContent(
      plain(`Dépenses ${formatMoney(45_000)} · Résultat ${formatMoney(565_000)}`),
    );
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(await screen.findByRole("button", { name: /^Dépenses du jour/ })).toBeVisible();
    await user.click(toggle);
    expect(screen.queryByRole("button", { name: /^Dépenses du jour/ })).toBeNull();
  });
});
