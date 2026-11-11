import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { axeViolations } from "../../testing/axe";
import {
  CATEGORIES,
  EXPENSES_PATH,
  expenseRoutes,
  NOW,
  preloadExpenses,
  route,
  setClock,
} from "../../testing/expensesApi";
import { apiError, json, type Call } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { BASE_LOCKED } from "./CategoryRow";

const SETTINGS = `${EXPENSES_PATH}?vue=reglages`;

beforeAll(preloadExpenses);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

const bodyOf = (calls: readonly Call[], key: string) =>
  calls.find((c) => `${c.method} ${c.url}` === key)?.body;

const rowOf = (name: string) => {
  const list = screen.getByRole("list", { name: "Catégories de dépense" });
  const row = within(list).getByText(name).closest("li");
  if (row === null) throw new Error(`Catégorie « ${name} » absente`);
  return within(row);
};

describe("Réglages des catégories et des tags (UC-DEP-02)", () => {
  it("catégorie de base : désactivation refusée avec la raison ; une autre se désactive", async () => {
    const groupe = CATEGORIES[5];
    if (groupe === undefined) throw new Error("fixture");
    const key = route("PATCH", "/expense-categories/cat-groupe");
    const { user, fake, container } = renderApp(SETTINGS, {
      ...expenseRoutes("owner"),
      [key]: json(200, { ...groupe, active: false, version: 2 }),
    });
    await screen.findByRole("list", { name: "Catégories de dépense" });
    expect(await axeViolations(container)).toEqual([]);
    const base = rowOf("Carburant").getByRole("button", { name: "Désactiver" });
    expect(base).toHaveAttribute("aria-disabled", "true");
    expect(base).toHaveAccessibleDescription(BASE_LOCKED);

    await user.click(rowOf("Groupe électrogène").getByRole("button", { name: "Désactiver" }));
    expect(await rowOf("Groupe électrogène").findByText("Désactivée")).toBeVisible();
    expect(bodyOf(fake.calls, key)).toEqual({ active: false, version: 1 });
  });

  it("BASE_CATEGORY_LOCKED renvoyé par le serveur : message explicite", async () => {
    const { user } = renderApp(SETTINGS, {
      ...expenseRoutes("owner"),
      [route("PATCH", "/expense-categories/cat-groupe")]: apiError(
        422,
        "BASE_CATEGORY_LOCKED",
        "x",
      ),
    });
    await screen.findByRole("list", { name: "Catégories de dépense" });
    await user.click(rowOf("Groupe électrogène").getByRole("button", { name: "Désactiver" }));
    expect(
      await screen.findByText("Une catégorie de base se renomme mais ne se désactive pas."),
    ).toBeVisible();
  });

  it("ajoute et renomme une catégorie", async () => {
    const loyer = CATEGORIES[3];
    if (loyer === undefined) throw new Error("fixture");
    const rename = route("PATCH", "/expense-categories/cat-loyer");
    const create = route("POST", "/expense-categories");
    const { user, fake } = renderApp(SETTINGS, {
      ...expenseRoutes("owner"),
      [rename]: json(200, { ...loyer, name: "Loyer boutique", version: 2 }),
      [create]: json(201, {
        ...loyer,
        id: "cat-new",
        name: "Transport",
        is_base: false,
        display_order: 7,
      }),
    });
    await screen.findByRole("list", { name: "Catégories de dépense" });
    await user.click(rowOf("Loyer").getByRole("button", { name: "Renommer" }));
    const field = screen.getByLabelText("Nouveau nom pour Loyer");
    await user.clear(field);
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(screen.getByText("Le nom est vide")).toBeVisible();
    await user.type(field, "Loyer boutique");
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByText("Loyer boutique")).toBeVisible();
    expect(bodyOf(fake.calls, rename)).toEqual({ name: "Loyer boutique", version: 1 });

    await user.click(screen.getByRole("button", { name: "Ajouter la catégorie" }));
    expect(screen.getByText("Le nom est vide")).toBeVisible();
    await user.type(screen.getByLabelText("Nouvelle catégorie"), "Transport");
    await user.click(screen.getByRole("button", { name: "Ajouter la catégorie" }));
    expect(await screen.findByText("Transport")).toBeVisible();
    expect(bodyOf(fake.calls, create)).toMatchObject({ name: "Transport" });
  });

  it("fusion de tags : confirmée avant l'envoi", async () => {
    const merge = route("POST", "/tags/merge");
    const { user, fake } = renderApp(SETTINGS, {
      ...expenseRoutes("owner"),
      [route("GET", "/tags?search=g")]: json(200, [
        { id: "t1", name: "groupe" },
        { id: "t2", name: "groupe électrogène" },
      ]),
      [merge]: json(200, {
        target: { id: "t2", name: "groupe électrogène" },
        retagged_expenses: 3,
      }),
    });
    await screen.findByRole("list", { name: "Catégories de dépense" });
    const button = () => screen.getByRole("button", { name: "Fusionner" });
    expect(button()).toHaveAccessibleDescription("Choisissez les deux tags à fusionner");

    await user.type(screen.getByLabelText("Tag à fusionner"), "g");
    const sources = await screen.findByRole("list", { name: "Tag à fusionner — tags trouvés" });
    await user.click(within(sources).getByRole("button", { name: "groupe" }));
    await user.type(screen.getByLabelText("Fusionner dans"), "g");
    const targets = await screen.findByRole("list", { name: "Fusionner dans — tags trouvés" });
    await user.click(within(targets).getByRole("button", { name: "groupe électrogène" }));

    await user.click(button());
    const dialog = screen.getByRole("dialog", {
      name: "Fusionner « groupe » dans « groupe électrogène » ?",
    });
    expect(fake.count(merge)).toBe(0);
    await user.click(within(dialog).getByRole("button", { name: "Fusionner" }));
    expect(
      await screen.findByText(
        "« groupe » fusionné dans « groupe électrogène » : 3 dépenses mises à jour.",
      ),
    ).toBeVisible();
    expect(bodyOf(fake.calls, merge)).toEqual({ source_id: "t1", target_id: "t2" });
  });
});
