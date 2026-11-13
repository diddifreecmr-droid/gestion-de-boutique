import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { axeViolations } from "../../testing/axe";
import { json, SHOP_A } from "../../testing/fakeApi";
import { money, plain, preloadSales, renderSale } from "../../testing/renderSale";
import { apparelSaleProfile } from "../../testing/salesCatalog";
import { cancelled, NOW, page, saleCommand } from "../../testing/salesFixtures";
import { addSale, API, saleServer } from "../../testing/salesServer";

const MY_SALES = `/s/${SHOP_A}/mes-ventes`;
const SALES = `/s/${SHOP_A}/ventes`;

beforeAll(preloadSales);
beforeEach(() => {
  window.localStorage.clear();
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(NOW));
});
afterEach(() => {
  vi.useRealTimers();
});

function at<T>(items: readonly T[], index: number): T {
  const item = items[index];
  if (item === undefined) throw new Error(`Élément ${String(index)} absent`);
  return item;
}

const salesList = () => screen.findByRole("list", { name: "Liste des ventes" });
const listCalls = (calls: readonly { method: string; url: string }[]) =>
  calls.filter((c) => c.method === "GET" && c.url.startsWith(`${API}/sales`)).map((c) => c.url);

describe("liste des ventes (UC-VEN-05)", () => {
  it("vendeur : ses ventes du jour, totaux, pastilles Crédit et Annulée, sans vendeur ni coût", async () => {
    const view = renderSale("seller", { path: MY_SALES });
    const credit = await addSale(
      view.server,
      saleCommand({
        kind: "credit",
        customer: {
          id: "cus-moussa",
          name: "Moussa Abdou",
          phone: "+237690000000",
          kind: "individual",
        },
        payments: [{ mode_id: "pm-orange", amount: 200_000, reference: null }],
      }),
    );
    const cash = await addSale(
      view.server,
      saleCommand({ lines: [{ ...at(saleCommand().lines, 0), details: [] }] }),
    );
    view.server.sales.set(cash.id, cancelled(cash, "Erreur"));

    const list = await salesList();
    const rows = within(list).getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    const [last, first] = [at(rows, 0), at(rows, 1)];
    expect(plain(last.textContent)).toMatch(/^V-000125.*Annulée/);
    expect(within(first).getByText("Crédit")).toBeVisible();
    expect(plain(first.textContent)).toContain("Orange Money");
    expect(plain(first.textContent)).not.toMatch(/par /);
    expect(within(last).getByText("V-000125")).toHaveClass("line-through");
    expect(screen.getByText("Ventes du 11/11/2026")).toBeVisible();
    expect(plain(screen.getByText(/1 vente · encaissé/).textContent)).toContain(money(200_000));
    expect(view.container.textContent).not.toMatch(/coût|marge|CMP/i);
    expect(listCalls(view.fake.calls)[0]).toBe(`${API}/sales`);
    expect(await axeViolations(view.container)).toEqual([]);
    expect(credit.number).toBe("V-000124");
  });

  it("total négatif (annulations du jour d'une vente plus ancienne) : affiché avec « − »", async () => {
    const server = saleServer("owner");
    const old = await addSale(server, saleCommand());
    const view = renderSale("owner", {
      path: SALES,
      extra: {
        [`GET ${API}/sales`]: json(
          200,
          page([cancelled(old, "Erreur")], {
            totals: { count: 0, total: -780_000, paid: -780_000 },
          }),
        ),
      },
    });
    await salesList();
    expect(plain(view.container.textContent)).toContain("Ventes du 11/11/2026−780 000FCFA");
    expect(view.container.innerHTML).not.toMatch(/overflow-x|w-max|min-w-max|w-screen/);
  });

  it("propriétaire : vendeur affiché, filtres période, mode, crédit et vendeur, recherche n°/châssis", async () => {
    const view = renderSale("owner", { path: SALES });
    await addSale(view.server, saleCommand());
    const list = await salesList();
    expect(plain(within(list).getByRole("listitem").textContent)).toContain("par vous");

    const { user } = view;
    await user.click(screen.getByRole("button", { name: "Période : Aujourd'hui" }));
    await user.click(screen.getByRole("radio", { name: "7 derniers jours" }));
    expect(screen.getByRole("button", { name: "Période : 7 derniers jours" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Filtres" }));
    await user.click(screen.getByRole("radio", { name: "Crédit" }));
    await user.click(screen.getByRole("radio", { name: "MTN MoMo" }));
    await user.click(screen.getByRole("radio", { name: "Issa Vendeur" }));
    expect(screen.getByRole("button", { name: "Filtres (3)" })).toBeVisible();
    await user.type(screen.getByLabelText("Chercher un n° de vente ou de châssis"), "lbx");
    await screen.findByRole("list", { name: "Liste des ventes" });
    const urls = listCalls(view.fake.calls);
    expect(urls).toContain(`${API}/sales?from=2026-11-05&to=2026-11-11`);
    expect(urls.at(-1)).toBe(
      `${API}/sales?q=lbx&kind=credit&payment_mode_id=pm-mtn&seller_id=01890a5d-ac96-774b-bcce-b302099a8010`,
    );
    expect(screen.queryByRole("radiogroup", { name: "Période" })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Période/ })).toBeNull(); // recherche : toutes dates
  });

  it("premier écran compact : période sur une ligne, total avant la liste ; « châssis » seulement pour Motos", async () => {
    const view = renderSale("seller", {
      path: MY_SALES,
      extra: { [`GET ${API}/profile`]: json(200, apparelSaleProfile("seller")) },
    });
    await addSale(view.server, saleCommand());
    const list = await salesList();
    expect(screen.getByLabelText("Chercher un n° de vente")).not.toHaveAccessibleDescription();
    expect(view.container.textContent).not.toMatch(/châssis/i);
    expect(screen.getByRole("button", { name: "Période : Aujourd'hui" })).toBeVisible();
    expect(screen.queryByRole("radiogroup", { name: "Période" })).toBeNull();
    const total = screen.getByText("Ventes du 11/11/2026");
    expect(total.compareDocumentPosition(list) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(await axeViolations(view.container)).toEqual([]);
  });

  it("aucune vente : message et « Nouvelle vente »", async () => {
    const { user, router } = renderSale("seller", { path: MY_SALES });
    expect(await screen.findByText("Aucune vente sur cette période.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Nouvelle vente" }));
    expect(router.state.location.pathname).toBe(`/s/${SHOP_A}/nouvelle-vente`);
  });
});
