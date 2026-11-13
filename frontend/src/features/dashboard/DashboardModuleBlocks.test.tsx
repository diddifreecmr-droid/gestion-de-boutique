/**
 * Tableau de bord : le bloc d'un module éteint vaut `null` (specs § 15.1) — il n'apparaît pas,
 * ni à zéro ; présent sinon. Cohérence avec `useModules()` : module éteint pour la coquille,
 * bloc caché même s'il est reçu. Modules à venir (`transfers`, `transport`, 13/11/2026) :
 * « Déplacements en route » et « Camions » n'apparaissent jamais, même reçus.
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
import { unfoldSections } from "../../testing/dashboardFold";
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
const blocks = ["expenses", "receivables"] as const;
type Block = (typeof blocks)[number];

const nulled: Record<Block, Partial<Dashboard>> = {
  expenses: { summary: { ...base.summary, expenses: null } },
  receivables: { receivables: null },
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

/** Chiffres lus, sections dépliées : chaque bloc présent est à l'écran. */
async function ready(user: Parameters<typeof unfoldSections>[0]) {
  await unfoldSections(user);
  return screen.findByRole("list", { name: "Stock" });
}
const expensesCard = () => screen.queryByRole("button", { name: /^Dépenses du jour/ });
const result = () => screen.queryByText(/^Résultat simple du jour/);
const list = (name: string) => screen.queryByRole("list", { name });

/** Le bloc du module est-il à l'écran ? */
const visible: Record<Block, () => boolean> = {
  expenses: () => expensesCard() !== null && result() !== null,
  receivables: () => list("Créances") !== null,
};

describe("tableau de bord — blocs des modules facultatifs", () => {
  it.each(blocks)("« %s » à null : son bloc seul disparaît, les autres restent", async (module) => {
    const { user } = open(dashboardBody(nulled[module]));
    await ready(user);
    expect(visible[module]()).toBe(false);
    for (const other of blocks.filter((m) => m !== module)) expect(visible[other]()).toBe(true);
  });

  it.each(blocks)("« %s » reçu, module éteint pour la coquille : caché aussi", async (module) => {
    const { user } = open(dashboardBody(), without(module));
    await ready(user);
    expect(visible[module]()).toBe(false);
  });

  it("boutique minimale : aucun bloc de module, aucun zéro inventé ; stock et marge restent ; axe", async () => {
    const all = Object.values(nulled).reduce<Partial<Dashboard>>(
      (merged, part) => ({ ...merged, ...part }),
      {},
    );
    const { container, user } = open(dashboardBody(all), MINIMAL);
    await ready(user);
    for (const module of blocks) expect(visible[module]()).toBe(false);
    expect(screen.getByRole("button", { name: /^Marge du jour/ })).toBeVisible();
    expect(screen.getByRole("button", { name: /Valeur du stock/ })).toHaveTextContent(
      "Au CMP, hors stock abîmé",
    );
    expect(document.body.textContent).not.toMatch(/Dépenses|Créances|Camions|en route/);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("tous les modules : chaque bloc est là ; jamais « Déplacements en route » ni « Camions » ; axe", async () => {
    const { container, user } = open(dashboardBody()); // blocs `in_transit` et `trucks` reçus
    await ready(user);
    for (const module of blocks) expect(visible[module]()).toBe(true);
    expect(screen.queryByText("Déplacements en route")).toBeNull();
    expect(list("Camions")).toBeNull();
    expect(screen.queryByText(/Dépenses de transport|Disponible au Lot/)).toBeNull();
    expect(screen.getByRole("button", { name: /Valeur du stock/ })).toHaveTextContent(
      "Au CMP, hors stock abîmé",
    );
    expect(await axeViolations(container)).toEqual([]);
  });
});
