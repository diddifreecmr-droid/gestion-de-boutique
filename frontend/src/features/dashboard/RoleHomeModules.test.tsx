/**
 * Accueils du comptable et du chauffeur (`GET /home`) : le bloc d'un module éteint vaut `null`
 * (specs § 15.1) et n'apparaît pas, ni à zéro ; présent sinon. Tuiles et bouton d'un module
 * éteint pour la coquille (`useModules()`) : absents.
 */
import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { AccountantHome, DriverHome } from "../../core/gateways/reportingContract";
import { ALL_MODULES, type ModuleCode } from "../../core/profile/modules";
import { axeViolations } from "../../testing/axe";
import {
  HOME,
  HOME_PATH,
  homeBody,
  homeRoutes,
  LOT_2,
  modulesProfile,
  NOW,
  preloadDashboard,
  PROFILE,
  TODAY,
} from "../../testing/dashboard";
import { setClock } from "../../testing/expensesApi";
import { json } from "../../testing/fakeApi";
import { MINIMAL } from "../../testing/modules";
import { renderApp } from "../../testing/renderApp";
import { DRIVER_NOTHING } from "./DriverHome";

beforeAll(preloadDashboard);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

const accountantBlock = homeBody("accountant").accountant;
if (accountantBlock === undefined) throw new Error("Accueil du comptable sans son bloc");

function openAccountant(
  block: Partial<AccountantHome>,
  modules: readonly ModuleCode[] = ALL_MODULES,
) {
  return renderApp(
    HOME_PATH,
    homeRoutes("accountant", {
      [HOME]: json(200, {
        role: "accountant",
        today: TODAY,
        accountant: { ...accountantBlock, ...block },
      }),
      [PROFILE]: modulesProfile(modules),
    }),
  );
}

function openDriver(block: DriverHome, modules: readonly ModuleCode[] = ALL_MODULES) {
  return renderApp(
    HOME_PATH,
    homeRoutes("driver", {
      [HOME]: json(200, { role: "driver", today: TODAY, driver: block }),
      [PROFILE]: modulesProfile(modules),
    }),
  );
}

const day = async () => within(await screen.findByRole("list", { name: "Ma journée" }));
const main = () => within(screen.getByRole("main"));

describe("accueil du comptable — modules", () => {
  it("dépenses et déplacements reçus : les deux lignes sont là", async () => {
    openAccountant({});
    const list = await day();
    expect(list.getByRole("button", { name: /Dépenses du jour/ })).toBeVisible();
    expect(list.getByText("Déplacements à réceptionner")).toBeVisible();
  });

  it.each([
    ["expenses", { expenses: null }, /Dépenses du jour/],
    ["transfers", { transfers_to_receive: null }, /Déplacements à réceptionner/],
  ] as const)("« %s » à null : sa ligne disparaît, sans zéro", async (_module, block, row) => {
    openAccountant(block);
    const list = await day();
    expect(list.queryByText(row)).toBeNull();
    expect(list.getByText("3 articles sous le seuil")).toBeVisible();
  });

  it("boutique minimale : ni ligne, ni tuile, ni bouton d'un module éteint ; axe", async () => {
    const { container } = openAccountant({ expenses: null, transfers_to_receive: null }, MINIMAL);
    const list = await day();
    expect(list.queryByText(/Dépenses du jour|Déplacements/)).toBeNull();
    expect(main().getByRole("button", { name: "Inventaire" })).toBeVisible();
    for (const name of ["Achat", "Dépense", "Déplacer du stock"]) {
      expect(main().queryByRole("button", { name })).toBeNull();
    }
    expect(screen.getByRole("main").textContent).not.toMatch(/0 FCFA/);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("dépenses reçues mais module éteint pour la coquille : ligne cachée", async () => {
    openAccountant(
      {},
      ALL_MODULES.filter((module) => module !== "expenses"),
    );
    const list = await day();
    expect(list.queryByText(/Dépenses du jour/)).toBeNull();
    expect(list.getByText("Déplacements à réceptionner")).toBeVisible();
  });
});

describe("accueil du chauffeur — module transport", () => {
  it("blocs à null : ni ligne ni zéro, une phrase simple ; axe", async () => {
    const { container } = openDriver({ current_trip: null, trip_expenses: null });
    expect(await screen.findByText(DRIVER_NOTHING)).toBeVisible();
    expect(screen.queryByRole("list", { name: "Mon voyage" })).toBeNull();
    expect(screen.getByRole("main").textContent).not.toMatch(/0 FCFA|Lot 2/);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("un seul bloc reçu : seule sa ligne apparaît", async () => {
    openDriver({ current_trip: LOT_2, trip_expenses: null });
    const list = within(await screen.findByRole("list", { name: "Mon voyage" }));
    expect(list.getByText("Voyage en cours")).toBeVisible();
    expect(list.queryByText("Mes dépenses de voyage")).toBeNull();
  });

  it("blocs reçus mais transport éteint pour la coquille : rien du voyage", async () => {
    openDriver(homeBody("driver").driver ?? { current_trip: LOT_2, trip_expenses: LOT_2 }, MINIMAL);
    expect(await screen.findByText(DRIVER_NOTHING)).toBeVisible();
  });
});
