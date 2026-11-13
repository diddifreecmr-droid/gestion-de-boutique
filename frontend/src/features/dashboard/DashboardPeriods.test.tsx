import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { formatMoney } from "../../shared/format";
import { axeViolations } from "../../testing/axe";
import {
  API,
  DASHBOARD_PATH,
  homeRoutes,
  NOW,
  preloadDashboard,
  TODAY,
  weekBody,
} from "../../testing/dashboard";
import { sectionToggle } from "../../testing/dashboardFold";
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

const WEEK = `GET ${API}/dashboard?period=week`;
const custom = (from: string, to: string) =>
  `GET ${API}/dashboard?period=custom&from=${from}&to=${to}`;
const money = (amount: number) => plain(formatMoney(amount));

describe("changer de période (UC-TDB-02)", () => {
  it("3 périodes + « Autre période » ; « Cette semaine » : chiffres, barres jour par jour, total et moyenne", async () => {
    const { user, router, fake, container } = renderApp(
      DASHBOARD_PATH,
      homeRoutes("owner", { [WEEK]: json(200, weekBody()) }),
    );
    const periods = await screen.findByRole("radiogroup", { name: "Période" });
    expect(
      within(periods)
        .getAllByRole("radio")
        .map((radio) => radio.textContent),
    ).toEqual(["Aujourd'hui", "Hier", "Ce mois", "Autre période"]);
    expect(screen.queryByRole("radiogroup", { name: "Autre période" })).toBeNull();
    // « Autre période » ouvre les autres choix et retient le premier, « Cette semaine ».
    await user.click(within(periods).getByRole("radio", { name: "Autre période" }));
    expect(router.state.location.search).toBe("?periode=week");
    const others = screen.getByRole("radiogroup", { name: "Autre période" });
    expect(
      within(others)
        .getAllByRole("radio")
        .map((radio) => radio.textContent),
    ).toEqual(["Cette semaine", "Mois dernier", "Période libre"]);
    expect(within(others).getByRole("radio", { name: "Cette semaine" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    const sales = await screen.findByRole("button", { name: /^Ventes de la semaine/ });
    expect(sales).toHaveTextContent("+12 % par rapport à la période précédente");
    expect(screen.getByText("Du 09/11/2026 au 11/11/2026")).toBeVisible();
    expect(fake.count(WEEK)).toBe(1);
    // Re-appuyer sur « Autre période » garde la période choisie.
    await user.click(within(periods).getByRole("radio", { name: "Autre période" }));
    expect(router.state.location.search).toBe("?periode=week");
    await user.click(await sectionToggle("Jour par jour"));

    const totals = screen.getByText("Total des ventes").closest("dl") ?? container;
    const terms = within(totals)
      .getAllByRole("term")
      .map((term) => term.textContent);
    expect(terms).toEqual([
      "Total des ventes",
      "Ventes en moyenne par jour",
      "Total de la marge",
      "Marge en moyenne par jour",
    ]);
    expect(totals).toHaveTextContent(
      `${money(3_340_000)}Ventes en moyenne par jour${money(1_113_333)}`,
    );

    const days = within(screen.getByRole("list", { name: "Ventes et marge par jour" }));
    const items = days.getAllByRole("listitem");
    expect(items.map((item) => plain(item.textContent))).toEqual([
      `09/11/2026Ventes${money(1_000_000)}Marge${money(200_000)}`,
      `10/11/2026Ventes${money(0)}Marge${money(-15_000)}`,
      `11/11/2026Ventes${money(2_340_000)}Marge${money(610_000)}`,
    ]);
    expect(within(items[1] ?? container).getByText(money(-15_000))).toHaveClass("text-danger-text");
    expect(container.innerHTML).not.toMatch(/overflow-x|w-max|min-w-max|w-screen/);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("aujourd'hui : pas de graphique (un seul jour)", async () => {
    renderApp(DASHBOARD_PATH, homeRoutes("owner"));
    await screen.findByRole("button", { name: /^Ventes du jour/ });
    expect(screen.queryByRole("list", { name: "Ventes et marge par jour" })).toBeNull();
  });

  it("période libre : du … au …, jamais après aujourd'hui ni à l'envers", async () => {
    const { user, fake, router } = renderApp(
      DASHBOARD_PATH,
      homeRoutes("owner", {
        [WEEK]: json(200, weekBody()),
        [custom(TODAY, TODAY)]: json(200, weekBody()),
        [custom("2026-11-01", TODAY)]: json(200, weekBody()),
      }),
    );
    await user.click(await screen.findByRole("radio", { name: "Autre période" }));
    await user.click(await screen.findByRole("radio", { name: "Période libre" }));
    expect(await screen.findByRole("button", { name: /^Ventes de la semaine/ })).toBeVisible();
    expect(fake.count(custom(TODAY, TODAY))).toBe(1);

    const to = screen.getByLabelText("Au");
    await user.clear(to);
    await user.type(to, "2026-11-12");
    expect(await screen.findByText("La période ne peut pas finir après aujourd'hui")).toBeVisible();
    expect(screen.queryByRole("button", { name: /^Ventes/ })).toBeNull();

    await user.clear(to);
    await user.type(to, "2026-11-01");
    expect(await screen.findByText("La date de début est après la date de fin")).toBeVisible();

    const from = screen.getByLabelText("Du");
    await user.clear(from);
    await user.type(from, "2026-11-01");
    await user.clear(to);
    await user.type(to, TODAY);
    expect(await screen.findByRole("button", { name: /^Ventes/ })).toBeVisible();
    expect(router.state.location.search).toBe(`?periode=custom&du=2026-11-01&au=${TODAY}`);
    expect(fake.count(custom("2026-11-01", TODAY))).toBe(1);
  });

  it("période libre vide : la date de début est demandée", async () => {
    renderApp(`${DASHBOARD_PATH}?periode=custom`, homeRoutes("owner"));
    expect(await screen.findByText("Choisissez la date de début")).toBeVisible();
    expect(screen.getByText("Choisissez une période valable")).toBeVisible();
  });
});
