import { configure, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import { listUrl } from "../../testing/catalog";
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

describe("matrice de stock — vendeur", () => {
  it("quantités par lieu, En route, Total, prix de base et pastilles ; aucun coût", async () => {
    const { container } = renderApp(STOCK_PAGE, stockRoutes("seller"));
    const haojue = await card(/Haojue/);
    if (haojue === undefined) throw new Error("carte Haojue absente");
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

  it("non-fuite : un coût envoyé par erreur au vendeur n'est jamais affiché", async () => {
    const leaked = { ...stockRow("owner"), wac: 123456, last_cost: 654321, wac_value: 999999 };
    const { container } = renderApp(
      STOCK_PAGE,
      stockRoutes("seller", { [matrixUrl()]: json(200, { locations: COLUMNS, items: [leaked] }) }),
    );
    await cards();
    expect(container).not.toHaveTextContent(money(123456));
    expect(container).not.toHaveTextContent(money(654321));
    expect(container).not.toHaveTextContent(money(999999));
  });

  it("360 px : des cartes (pas de table), aucun conteneur qui élargit la page", async () => {
    const { container } = renderApp(STOCK_PAGE, stockRoutes("seller"));
    const list = await cards();
    expect(container.querySelector("table")).toBeNull();
    expect(container.innerHTML).not.toMatch(/overflow-x|w-max|min-w-max|w-screen/);
    for (const term of within(list).getAllByRole("term")) {
      expect(term.className).toMatch(/min-w-0/);
      expect(term.className).toMatch(/break-words/);
    }
  });
});

describe("matrice de stock — propriétaire et comptable", () => {
  it("propriétaire : onglets, actions, prix de base et coûts ; onglet Articles = catalogue", async () => {
    const { container, user, router } = renderApp(
      STOCK_PAGE,
      stockRoutes("owner", { [listUrl()]: json(200, { items: [], next_cursor: null }) }),
    );
    const haojue = await card(/Haojue/);
    expect(haojue).toHaveTextContent(`Dernier coût${money(650000)}`);
    expect(haojue).toHaveTextContent(`Coût moyen (CMP)${money(640000)}`);
    expect(haojue).toHaveTextContent(`Valeur au CMP${money(640000)}`);
    expect(await card(/Yamaha/)).toHaveTextContent("Coût moyen (CMP)non calculable");
    const tabs = screen.getByRole("navigation", { name: "Section Stock" });
    expect(within(tabs).getByRole("link", { name: "Stock" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("button", { name: "Valeur du stock" })).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(tabs).getByRole("link", { name: "Articles" }));
    expect(router.state.location.search).toBe("?vue=articles");
    expect(await screen.findByRole("heading", { name: "Articles" })).toBeVisible();
  });

  it("comptable : coûts sans prix de base ; « Historique » ouvre la fiche stock", async () => {
    const { user, router } = renderApp(STOCK_PAGE, stockRoutes("accountant"));
    const haojue = await card(/Haojue/);
    if (haojue === undefined) throw new Error("carte Haojue absente");
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
