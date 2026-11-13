/**
 * Liste du stock compacte (audit UX du 13/11/2026) : sur la ligne, le nom, la quantité totale
 * et la pastille ; le détail (lieux, prix, coûts selon le rôle) à un appui. « En route » suit
 * le module `transfers`.
 */
import { configure, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import { API, profileBody } from "../../testing/catalog";
import { json } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { COLUMNS, matrixUrl, STOCK_PAGE, stockRoutes, stockRow } from "../../testing/stock";
import { openStockItem, stockItem, stockList } from "../../testing/stockList";

configure({ asyncUtilTimeout: 5000 });

beforeEach(() => {
  window.localStorage.clear();
});

describe("liste du stock compacte", () => {
  it("ligne : nom, total et pastille ; un appui déplie le détail, un autre le replie", async () => {
    const { container, user } = renderApp(STOCK_PAGE, stockRoutes("seller"));
    const haojue = await stockItem(/Haojue/);
    const row = within(haojue).getByRole("button", { name: /Haojue/ });
    expect(row).toHaveAttribute("aria-expanded", "false");
    expect(row).toHaveTextContent("Haojue HJ125-8En stock1Stock bas");
    expect(within(haojue).queryAllByRole("term")).toEqual([]);
    expect(within(await stockList()).getByText("Rupture")).toBeVisible();
    await user.click(row);
    expect(row).toHaveAttribute("aria-expanded", "true");
    expect(
      within(haojue)
        .getAllByRole("term")
        .map((term) => term.textContent),
    ).toEqual(["Garoua", "Ngaoundéré", "Total", "Prix de base"]);
    expect(await axeViolations(container)).toEqual([]);
    await user.click(row);
    expect(within(haojue).queryAllByRole("term")).toEqual([]);
  });

  it("propriétaire : aucun prix ni coût (ni « non calculable ») sur les lignes fermées", async () => {
    renderApp(STOCK_PAGE, stockRoutes("owner"));
    expect(await stockList()).not.toHaveTextContent(/coût|CMP|Valeur|Prix|non calculable/i);
    expect(screen.queryByRole("button", { name: "Valeur du stock" })).toBeNull();
  });

  it("module `transfers` éteint : pas de « En route », sauf une quantité réellement en route", async () => {
    const moving = stockRow("seller", {
      article_id: "a-moving",
      display_name: "Sym Jet",
      incoming: "2.000",
    });
    const { user } = renderApp(
      STOCK_PAGE,
      stockRoutes("seller", {
        [`GET ${API}/profile`]: json(200, {
          ...profileBody("seller"),
          enabled_modules: ["core", "audit", "catalog", "sales"],
        }),
        [matrixUrl()]: json(200, { locations: COLUMNS, items: [stockRow("seller"), moving] }),
      }),
    );
    const haojue = await openStockItem(user, /Haojue/);
    expect(within(haojue).queryByText("En route")).toBeNull();
    const sym = await openStockItem(user, /Sym Jet/);
    expect(within(sym).getByText("En route")).toBeVisible();
  });
});
