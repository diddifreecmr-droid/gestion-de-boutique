import { configure, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import { json } from "../../testing/fakeApi";
import { money } from "../../testing/renderSale";
import { renderApp } from "../../testing/renderApp";
import { API, GAROUA, HAOJUE_ID, STOCK_PAGE, stockRoutes, valuation } from "../../testing/stock";

configure({ asyncUtilTimeout: 5000 });

beforeEach(() => {
  window.localStorage.clear();
});

const VALUE = `GET ${API}/stock/value`;
const DAMAGED = `GET ${API}/stock/damaged`;
const unknown = valuation({ at_wac: null, at_wac_known: 640000, without_wac: 2 });
const report = {
  locations: [
    {
      location_id: GAROUA,
      location_name: "Garoua",
      active: true,
      sellable: unknown,
      damaged: valuation({ at_wac: 0, at_last_cost: 0 }),
      incoming: valuation({ at_wac: 0, at_last_cost: 0 }),
    },
  ],
  sellable: unknown,
  damaged: valuation({ at_wac: 640000, at_last_cost: 650000 }),
  incoming: valuation({ at_wac: 0, at_last_cost: 0 }),
};

describe("valeur du stock (UC-STK-10)", () => {
  it("non calculable : part connue et articles sans coût ; vue au dernier coût ; abîmé à part", async () => {
    const { user, container } = renderApp(
      `${STOCK_PAGE}?vue=valeur`,
      stockRoutes("accountant", { [VALUE]: json(200, report) }),
    );
    expect(await screen.findByText("non calculable")).toBeVisible();
    expect(screen.getByText(`Part connue : ${money(640000)}`)).toBeVisible();
    expect(screen.getByText("2 articles sans coût connu")).toBeVisible();
    const places = screen.getByRole("list", { name: "Valeur par lieu" });
    expect(within(places).getByRole("listitem")).toHaveTextContent(
      `Vendablenon calculable (connu : ${money(640000)}, 2 articles sans coût connu)`,
    );
    expect(container).toHaveTextContent(`Stock abîmé${money(640000)}`);
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("radio", { name: "Au dernier coût" }));
    expect(screen.getByText("Stock vendable, tous lieux, au dernier coût")).toBeVisible();
    expect(container).toHaveTextContent(`Stock abîmé${money(650000)}`);
  });

  it("le vendeur n'y a pas accès : l'adresse ouvre la matrice, sans appel à la valeur", async () => {
    const { fake } = renderApp(`${STOCK_PAGE}?vue=valeur`, stockRoutes("seller"));
    expect(await screen.findByRole("list", { name: "Stock par article" })).toBeVisible();
    expect(fake.calls.some((call) => call.url.includes("/stock/value"))).toBe(false);
  });
});

describe("stock abîmé", () => {
  it("liste par article et lieu, valeur au CMP ou non calculable", async () => {
    const items = [
      {
        article_id: HAOJUE_ID,
        display_name: "Haojue HJ125-8",
        stock_unit: "UNIT",
        location_id: GAROUA,
        location_name: "Garoua",
        damaged: "1.000",
        wac: null,
        wac_value: null,
      },
    ];
    const { container, user } = renderApp(
      `${STOCK_PAGE}?vue=valeur`,
      stockRoutes("owner", { [VALUE]: json(200, report), [DAMAGED]: json(200, { items }) }),
    );
    await user.click(await screen.findByRole("button", { name: "Voir le stock abîmé" }));
    const list = await screen.findByRole("list", { name: "Stock abîmé" });
    expect(list).toHaveTextContent("LieuGarouaQuantité abîmée1Valeur au CMPnon calculable");
    expect(await axeViolations(container)).toEqual([]);
  });

  it("aucun stock abîmé", async () => {
    renderApp(
      `${STOCK_PAGE}?vue=abime`,
      stockRoutes("owner", { [DAMAGED]: json(200, { items: [] }) }),
    );
    expect(await screen.findByText("Aucun stock abîmé.")).toBeVisible();
  });
});
