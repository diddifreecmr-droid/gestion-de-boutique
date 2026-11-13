import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { formatMoney, NBSP } from "../../shared/format";
import { axeViolations } from "../../testing/axe";
import {
  DASHBOARD_TODAY,
  dashboardBody,
  DASHBOARD_PATH,
  homeRoutes,
  NOW,
  preloadDashboard,
} from "../../testing/dashboard";
import { setClock } from "../../testing/expensesApi";
import { json } from "../../testing/fakeApi";
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

/** « 2 340 000 » : le nombre d'un `KpiCard` (l'unité FCFA est dans un autre élément). */
const figure = (amount: number) => plain(formatMoney(amount).replace(`${NBSP}FCFA`, ""));
const card = (name: RegExp) => screen.findByRole("button", { name });
const list = (name: string) => within(screen.getByRole("list", { name }));

describe("tableau de bord du propriétaire (UC-TDB-01, design-system § 7.2)", () => {
  it("tous les blocs, de haut en bas, avec la comparaison en mots ; 360 px, axe", async () => {
    const { container, fake } = renderApp(DASHBOARD_PATH, homeRoutes("owner"));
    const sales = await card(/^Ventes du jour/);
    expect(sales).toHaveTextContent(plain(figure(2_340_000)));
    expect(sales).toHaveTextContent(plain("3 ventes"));
    expect(sales).toHaveTextContent(plain(`+12${NBSP}% par rapport à hier`));
    const collected = await card(/^Argent encaissé du jour/);
    expect(collected).toHaveTextContent(plain(figure(1_100_000)));
    expect(collected).toHaveTextContent(
      plain(`Pas de comparaison possible (hier : ${formatMoney(0)})`),
    );
    const margin = await card(/^Marge du jour/);
    expect(margin).toHaveTextContent(plain(`−13${NBSP}% par rapport à hier`));
    expect(margin).toHaveTextContent(plain(`Taux de marge : 26,07${NBSP}%`));
    expect(await card(/^Dépenses du jour/)).toHaveTextContent(plain(figure(45_000)));
    expect(screen.getByText(/^Résultat simple du jour/).closest("div")).toHaveTextContent(
      plain(figure(565_000)),
    );

    expect(list("Créances").getByRole("button", { name: /Total à recevoir/ })).toHaveTextContent(
      plain(`4 clients débiteurs${formatMoney(1_800_000)}`),
    );
    expect(list("Créances").getByText("2 rappels à faire")).toBeVisible();
    expect(list("Stock").getByRole("button", { name: /Valeur du stock/ })).toHaveTextContent(
      plain(formatMoney(12_500_000)),
    );
    expect(list("Stock").getByText("3 articles sous le seuil")).toBeVisible();
    expect(list("Stock").getByText("1 quantité négative")).toBeVisible();
    expect(screen.queryByText("Disponible au Lot 2")).toBeNull(); // modules à venir
    expect(screen.queryByRole("list", { name: "Camions" })).toBeNull();
    expect(list("Erreurs signalées").getByText("2 erreurs à traiter")).toBeVisible();
    expect(
      await within(await screen.findByRole("list", { name: "Alertes en attente" })).findByText(
        "Aucune demande en attente",
      ),
    ).toBeVisible();
    expect(list("Ventes sans coût connu").getByText("1 vente sans coût connu")).toBeVisible();
    expect(fake.count(DASHBOARD_TODAY)).toBe(1);

    expect(container.querySelector("table")).toBeNull();
    expect(container.innerHTML).not.toMatch(/overflow-x|w-max|min-w-max|w-screen/);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("« Voir aussi au CMP » : marge au CMP à côté de la marge au dernier coût, avec l'écart", async () => {
    const { user } = renderApp(DASHBOARD_PATH, homeRoutes("owner"));
    await user.click(await screen.findByRole("button", { name: "Voir aussi au CMP" }));
    const terms = screen.getAllByRole("term").map((term) => term.textContent);
    expect(terms).toEqual(["Marge au dernier coût", "Marge au CMP", "Écart (CMP − dernier coût)"]);
    const values = screen.getAllByRole("definition").map((value) => value.textContent);
    expect(values).toEqual([formatMoney(610_000), formatMoney(650_000), `+${formatMoney(40_000)}`]);
  });

  it("aucune vente sans coût : la ligne n'apparaît pas ; stock non calculable dit pourquoi", async () => {
    const body = dashboardBody();
    renderApp(
      DASHBOARD_PATH,
      homeRoutes("owner", {
        [DASHBOARD_TODAY]: json(200, {
          ...body,
          summary: { ...body.summary, without_cost: 0, margin_rate_pct: null },
          stock: {
            ...body.stock,
            value: { ...body.stock.value, at_wac: null, at_wac_known: 900_000, without_wac: 2 },
          },
        }),
      }),
    );
    expect(await card(/^Marge du jour/)).toHaveTextContent(plain("Taux de marge non calculable"));
    expect(screen.queryByRole("list", { name: "Ventes sans coût connu" })).toBeNull();
    expect(list("Stock").getByRole("button", { name: /Valeur du stock/ })).toHaveTextContent(
      plain(`Non calculable : 2 articles sans coût connu (connu : ${formatMoney(900_000)})`),
    );
  });
});

describe("hors connexion (RG-T25)", () => {
  it("« Chiffres disponibles avec internet » à la place des montants ; les accès restent", async () => {
    const { user, fake } = renderApp(
      DASHBOARD_PATH,
      homeRoutes("owner", { [DASHBOARD_TODAY]: new TypeError("Failed to fetch") }),
    );
    expect(await screen.findAllByText("Chiffres disponibles avec internet")).toHaveLength(2);
    expect(screen.queryByRole("button", { name: /^Ventes du jour/ })).toBeNull();
    expect(plain(document.body.textContent)).not.toContain(figure(2_340_000));
    expect(screen.getByRole("radiogroup", { name: "Période" })).toBeVisible();
    expect(await screen.findByRole("list", { name: "Alertes en attente" })).toBeVisible();
    const before = fake.count(DASHBOARD_TODAY);
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(fake.count(DASHBOARD_TODAY)).toBeGreaterThan(before);
  });

  it("chiffres déjà lus puis réseau perdu : ils disparaissent, jamais de chiffre en cache", async () => {
    renderApp(DASHBOARD_PATH, homeRoutes("owner"));
    expect(await card(/^Ventes du jour/)).toHaveTextContent(plain(figure(2_340_000)));
    window.dispatchEvent(new Event("offline"));
    expect(await screen.findAllByText("Chiffres disponibles avec internet")).toHaveLength(2);
    expect(plain(document.body.textContent)).not.toContain(figure(2_340_000));
    window.dispatchEvent(new Event("online"));
    expect(await card(/^Ventes du jour/)).toHaveTextContent(plain(figure(2_340_000)));
  });
});
