import { configure, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import { API, listUrl, profileBody } from "../../testing/catalog";
import { json } from "../../testing/fakeApi";
import { money } from "../../testing/renderSale";
import { renderApp } from "../../testing/renderApp";
import {
  COLUMNS,
  GAROUA,
  HAOJUE_ID,
  matrixBody,
  matrixUrl,
  STOCK_PAGE,
  stockRoutes,
  stockRow,
} from "../../testing/stock";

configure({ asyncUtilTimeout: 5000 });

beforeEach(() => {
  window.localStorage.clear();
});

const cards = () => screen.findByRole("list", { name: "Stock par article" });
const card = async (name: RegExp) =>
  within(await cards())
    .getAllByRole("listitem")
    .find((item) => name.test(item.textContent));
/** Ligne d'un article, dépliée d'un appui : le détail (lieux, prix, coûts) apparaît dessous. */
const opened = async (user: { click: (element: Element) => Promise<void> }, name: RegExp) => {
  const item = await card(name);
  if (item === undefined) throw new Error(`ligne ${name.source} absente`);
  await user.click(within(item).getByRole("button", { name }));
  return item;
};

describe("matrice de stock — vendeur", () => {
  it("ligne compacte : nom, total et pastille ; un appui déplie le détail", async () => {
    const { container, user } = renderApp(STOCK_PAGE, stockRoutes("seller"));
    const haojue = await card(/Haojue/);
    if (haojue === undefined) throw new Error("ligne Haojue absente");
    const row = within(haojue).getByRole("button", { name: /Haojue/ });
    expect(row).toHaveAttribute("aria-expanded", "false");
    expect(row).toHaveTextContent("Haojue HJ125-8En stock1Stock bas");
    expect(within(haojue).queryAllByRole("term")).toEqual([]);
    expect(within(await cards()).getByText("Rupture")).toBeVisible();
    await user.click(row);
    expect(row).toHaveAttribute("aria-expanded", "true");
    expect(
      within(haojue)
        .getAllByRole("term")
        .map((term) => term.textContent),
    ).toEqual(["Garoua", "Ngaoundéré", "En route", "Total", "Prix de base"]);
    await user.click(row);
    expect(within(haojue).queryAllByRole("term")).toEqual([]);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("détail : quantités par lieu, En route, Total, prix de base et pastilles ; aucun coût", async () => {
    const { container, user } = renderApp(STOCK_PAGE, stockRoutes("seller"));
    const haojue = await opened(user, /Haojue/);
    await opened(user, /Yamaha/);
    const lines = within(haojue)
      .getAllByRole("term")
      .map((term) => term.textContent);
    expect(lines).toEqual(["Garoua", "Ngaoundéré", "En route", "Total", "Prix de base"]);
    expect(haojue).toHaveTextContent("Ngaoundéré0 (+ 1 abîmé)");
    expect(haojue).toHaveTextContent(`Prix de base${money(780000)}`);
    expect(within(haojue).getByText("Stock bas")).toBeVisible();
    expect(within(await cards()).getByText("Rupture")).toBeVisible();
    expect(container).not.toHaveTextContent(/coût|CMP|Valeur/i);
    expect(screen.queryByRole("navigation", { name: "Section Stock" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Inventaire" })).toBeNull();
    expect(screen.queryByRole("button", { name: /Historique/ })).toBeNull();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("module `transfers` éteint : pas de ligne « En route », sauf une quantité réellement en route", async () => {
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
    const haojue = await opened(user, /Haojue/);
    expect(within(haojue).queryByText("En route")).toBeNull();
    const sym = await opened(user, /Sym Jet/);
    expect(within(sym).getByText("En route")).toBeVisible();
  });

  it("non-fuite : un coût envoyé par erreur au vendeur n'est jamais affiché", async () => {
    const leaked = { ...stockRow("owner"), wac: 123456, last_cost: 654321, wac_value: 999999 };
    const { container, user } = renderApp(
      STOCK_PAGE,
      stockRoutes("seller", { [matrixUrl()]: json(200, { locations: COLUMNS, items: [leaked] }) }),
    );
    await opened(user, /Haojue/);
    expect(container).not.toHaveTextContent(money(123456));
    expect(container).not.toHaveTextContent(money(654321));
    expect(container).not.toHaveTextContent(money(999999));
  });

  it("360 px : des lignes (pas de table), aucun conteneur qui élargit la page", async () => {
    const { container, user } = renderApp(STOCK_PAGE, stockRoutes("seller"));
    const list = await cards();
    await opened(user, /Haojue/);
    expect(container.querySelector("table")).toBeNull();
    expect(container.innerHTML).not.toMatch(/overflow-x|w-max|min-w-max|w-screen/);
    for (const term of within(list).getAllByRole("term")) {
      expect(term.className).toMatch(/min-w-0/);
      expect(term.className).toMatch(/break-words/);
    }
  });
});

describe("matrice de stock — propriétaire et comptable", () => {
  it("propriétaire : onglets, outils repliés, prix de base et coûts ; onglet Articles = catalogue", async () => {
    const { container, user, router } = renderApp(
      STOCK_PAGE,
      stockRoutes("owner", { [listUrl()]: json(200, { items: [], next_cursor: null }) }),
    );
    const list = await cards();
    // Liste compacte : aucun prix ni coût (ni « non calculable ») sur les lignes fermées.
    expect(list).not.toHaveTextContent(/coût|CMP|Valeur|Prix|non calculable/i);
    const haojue = await opened(user, /Haojue/);
    expect(haojue).toHaveTextContent(`Dernier coût${money(650000)}`);
    expect(haojue).toHaveTextContent(`Coût moyen (CMP)${money(640000)}`);
    expect(haojue).toHaveTextContent(`Valeur au CMP${money(640000)}`);
    expect(await opened(user, /Yamaha/)).toHaveTextContent("Coût moyen (CMP)non calculable");
    const tabs = screen.getByRole("navigation", { name: "Section Stock" });
    expect(within(tabs).getByRole("link", { name: "Stock" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.queryByRole("button", { name: "Valeur du stock" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Outils du stock" }));
    const tools = within(screen.getByRole("navigation", { name: "Outils du stock" }));
    expect(tools.getAllByRole("button").map((button) => button.textContent)).toEqual([
      "Ajustement",
      "Inventaire",
      "Valeur du stock",
      "Stock abîmé",
    ]);
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(tabs).getByRole("link", { name: "Articles" }));
    expect(router.state.location.search).toBe("?vue=articles");
    expect(await screen.findByRole("heading", { name: "Articles" })).toBeVisible();
  });

  it("comptable : coûts sans prix de base ; « Historique » ouvre la fiche stock", async () => {
    const { user, router } = renderApp(STOCK_PAGE, stockRoutes("accountant"));
    const haojue = await opened(user, /Haojue/);
    expect(haojue).not.toHaveTextContent("Prix de base");
    expect(haojue).toHaveTextContent(`Coût moyen (CMP)${money(640000)}`);
    await user.click(within(haojue).getByRole("button", { name: /Historique/ }));
    expect(router.state.location.search).toBe(`?vue=mouvements&id=${HAOJUE_ID}`);
  });

  it("recherche dès la 1re lettre, filtre par lieu, tri par quantité", async () => {
    const one = json(200, { locations: COLUMNS, items: [stockRow("owner")] });
    const garoua = json(200, { locations: [COLUMNS[0]], items: [stockRow("owner")] });
    const { user, fake } = renderApp(
      STOCK_PAGE,
      stockRoutes("owner", {
        [matrixUrl("h")]: one,
        [matrixUrl(null, GAROUA)]: garoua,
        [matrixUrl(null, GAROUA, "quantity_asc")]: garoua,
        [matrixUrl("zz")]: json(200, { locations: COLUMNS, items: [] }),
      }),
    );
    await cards();
    await user.type(screen.getByLabelText("Rechercher un article"), "h");
    expect(fake.count(matrixUrl("h"))).toBe(1);
    await waitFor(() => {
      expect(screen.queryByText("Yamaha Crypton")).toBeNull();
    });
    expect(screen.getByText("Haojue HJ125-8")).toBeVisible();
    await user.clear(screen.getByLabelText("Rechercher un article"));
    await user.type(screen.getByLabelText("Rechercher un article"), "zz");
    expect(await screen.findByText("Aucun article ne correspond à « zz ».")).toBeVisible();
    await user.clear(screen.getByLabelText("Rechercher un article"));
    await user.click(screen.getByRole("button", { name: "Filtrer et trier" }));
    await user.click(await screen.findByRole("radio", { name: "Garoua" }));
    await user.click(screen.getByRole("radio", { name: "Moins en stock" }));
    expect(await cards()).toBeVisible();
    expect(fake.count(matrixUrl(null, GAROUA, "quantity_asc"))).toBe(1);
    // Le choix des lieux reste complet même filtré sur un seul lieu.
    expect(screen.getByRole("radio", { name: "Ngaoundéré" })).toBeVisible();
  });

  it("hors connexion : le dit et propose de réessayer", async () => {
    const { user } = renderApp(
      STOCK_PAGE,
      stockRoutes("owner", {
        [matrixUrl()]: [new TypeError("Failed to fetch"), json(200, matrixBody("owner"))],
      }),
    );
    await user.click(await screen.findByRole("button", { name: "Réessayer" }));
    expect(await cards()).toBeVisible();
  });
});
