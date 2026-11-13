/**
 * Tableau de bord : le bloc d'un module éteint vaut `null` (specs § 15.1) — il n'apparaît pas,
 * ni à zéro ; présent sinon. Cohérence avec `useModules()` : module éteint pour la coquille,
 * bloc caché même s'il est reçu.
 */
import { screen } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { Dashboard } from "../../core/gateways/reportingContract";
import { ALL_MODULES, type ModuleCode } from "../../core/profile/modules";
import { axeViolations } from "../../testing/axe";
import {
  DASHBOARD_PATH,
  DASHBOARD_TODAY,
  dashboardBody,
  homeRoutes,
  modulesProfile,
  NOW,
  preloadDashboard,
  PROFILE,
} from "../../testing/dashboard";
import { setClock } from "../../testing/expensesApi";
import { json } from "../../testing/fakeApi";
import { MINIMAL, without } from "../../testing/modules";
import { renderApp } from "../../testing/renderApp";

beforeAll(preloadDashboard);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

const base = dashboardBody();
const blocks = ["expenses", "receivables", "transfers", "transport"] as const;
type Block = (typeof blocks)[number];

const nulled: Record<Block, Partial<Dashboard>> = {
  expenses: { summary: { ...base.summary, expenses: null } },
  receivables: { receivables: null },
  transfers: { stock: { ...base.stock, in_transit: null } },
  transport: { trucks: null },
};

function open(body: Dashboard, modules: readonly ModuleCode[] = ALL_MODULES) {
  return renderApp(
    DASHBOARD_PATH,
    homeRoutes("owner", {
      [DASHBOARD_TODAY]: json(200, body),
      [PROFILE]: modulesProfile([...modules, "dashboard"]),
    }),
  );
}

const ready = () => screen.findByRole("list", { name: "Stock" });
const expensesCard = () => screen.queryByRole("button", { name: /^Dépenses du jour/ });
const result = () => screen.queryByText(/^Résultat simple du jour/);
const list = (name: string) => screen.queryByRole("list", { name });
const inTransit = () => screen.queryByText("Déplacements en route");

/** Le bloc du module est-il à l'écran ? */
const visible: Record<Block, () => boolean> = {
  expenses: () => expensesCard() !== null && result() !== null,
  receivables: () => list("Créances") !== null,
  transfers: () => inTransit() !== null,
  transport: () => list("Camions") !== null,
};

describe("tableau de bord — blocs des modules facultatifs", () => {
  it.each(blocks)("« %s » à null : son bloc seul disparaît, les autres restent", async (module) => {
    open(dashboardBody(nulled[module]));
    await ready();
    expect(visible[module]()).toBe(false);
    for (const other of blocks.filter((m) => m !== module)) expect(visible[other]()).toBe(true);
  });

  it.each(blocks)("« %s » reçu, module éteint pour la coquille : caché aussi", async (module) => {
    // Transport dépend de Transferts : éteindre Transferts éteint aussi Transport.
    open(dashboardBody(), module === "transfers" ? without(module, "transport") : without(module));
    await ready();
    expect(visible[module]()).toBe(false);
  });

  it("boutique minimale : aucun bloc de module, aucun zéro inventé ; stock et marge restent ; axe", async () => {
    const all = Object.values(nulled).reduce<Partial<Dashboard>>(
      (merged, part) => ({ ...merged, ...part }),
      {},
    );
    const { container } = open(dashboardBody(all), MINIMAL);
    await ready();
    for (const module of blocks) expect(visible[module]()).toBe(false);
    expect(screen.getByRole("button", { name: /^Marge du jour/ })).toBeVisible();
    expect(screen.getByRole("button", { name: /Valeur du stock/ })).toHaveTextContent(
      "Au CMP, hors stock abîmé",
    );
    expect(document.body.textContent).not.toMatch(/Dépenses|Créances|Camions|en route/);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("tous les modules : chaque bloc est là, « hors stock abîmé et en route »", async () => {
    open(dashboardBody());
    await ready();
    for (const module of blocks) expect(visible[module]()).toBe(true);
    expect(screen.getByRole("button", { name: /Valeur du stock/ })).toHaveTextContent(
      "hors stock abîmé et en route",
    );
  });
});
