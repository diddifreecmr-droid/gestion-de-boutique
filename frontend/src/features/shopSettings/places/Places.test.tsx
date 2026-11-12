import { screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../../testing/axe";
import { apiError, json, type Call } from "../../../testing/fakeApi";
import { renderApp } from "../../../testing/renderApp";
import {
  location,
  mode,
  preloadSettings,
  route,
  settingsRoutes,
  viewPath,
} from "../../../testing/shopSettingsApi";

beforeAll(preloadSettings);
beforeEach(() => {
  window.localStorage.clear();
});

const bodyOf = (calls: readonly Call[], key: string) =>
  calls.find((c) => `${c.method} ${c.url}` === key)?.body;

const rowIn = (listName: string, name: string) => {
  const list = screen.getByRole("list", { name: listName });
  const row = within(list).getByText(name).closest("li");
  if (row === null) throw new Error(`« ${name} » absent de « ${listName} »`);
  return within(row);
};

describe("Lieux (UC-SOC-05)", () => {
  const LIST = "Lieux de la boutique";

  it("liste les lieux, ajoute un entrepôt hors point de vente ; axe", async () => {
    const create = route("POST", "/locations");
    const added = location({
      id: "loc-boulai",
      name: "Garoua-Boulaï",
      kind: "warehouse",
      is_point_of_sale: false,
      city: null,
      display_order: 3,
    });
    const { user, fake, container } = renderApp(viewPath("lieux"), {
      ...settingsRoutes("owner"),
      [create]: json(201, added),
    });
    await screen.findByRole("list", { name: LIST });
    expect(rowIn(LIST, "Garoua").getByText("Point de vente")).toBeVisible();
    expect(rowIn(LIST, "Ngaoundéré").getByText(/Entrepôt/)).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);

    await user.click(screen.getByRole("button", { name: "Ajouter le lieu" }));
    expect(screen.getByText("Le nom est vide")).toBeVisible();
    await user.type(screen.getByLabelText("Nouveau lieu — nom"), "Garoua-Boulaï");
    const kind = screen.getByRole("radiogroup", { name: "Nouveau lieu — type" });
    await user.click(within(kind).getByRole("radio", { name: "Entrepôt" }));
    const sale = screen.getByRole("radiogroup", { name: "Nouveau lieu — point de vente" });
    await user.click(within(sale).getByRole("radio", { name: "Non" }));
    await user.click(screen.getByRole("button", { name: "Ajouter le lieu" }));
    expect(await screen.findByText("Garoua-Boulaï")).toBeVisible();
    expect(bodyOf(fake.calls, create)).toMatchObject({
      name: "Garoua-Boulaï",
      kind: "warehouse",
      is_point_of_sale: false,
      city: null,
      display_order: 3,
    });
  });

  it("modifie un lieu ; dernier point de vente : désactivation refusée avec la raison", async () => {
    const patch = route("PATCH", "/locations/loc-garoua");
    const { user, fake } = renderApp(viewPath("lieux"), {
      ...settingsRoutes("owner"),
      [patch]: [
        json(200, location({ name: "Garoua centre", version: 2 })),
        apiError(422, "LAST_POINT_OF_SALE", "x"),
      ],
    });
    await screen.findByRole("list", { name: LIST });
    await user.click(rowIn(LIST, "Garoua").getByRole("button", { name: "Modifier" }));
    const name = screen.getByLabelText("Modifier Garoua — nom");
    await user.clear(name);
    await user.type(name, "Garoua centre");
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByText("Garoua centre")).toBeVisible();
    expect(bodyOf(fake.calls, patch)).toEqual({
      name: "Garoua centre",
      kind: "store",
      is_point_of_sale: true,
      city: "Garoua",
      version: 1,
    });
    await user.click(rowIn(LIST, "Garoua centre").getByRole("button", { name: "Désactiver" }));
    expect(
      await screen.findByText("La boutique doit garder au moins un point de vente actif."),
    ).toBeVisible();
  });
});

describe("Modes de paiement (UC-SOC-06, SET-03)", () => {
  const LIST = "Modes de paiement";

  it("ajoute « Wave » avec référence obligatoire ; axe", async () => {
    const create = route("POST", "/payment-modes");
    const { user, fake, container } = renderApp(viewPath("modes"), {
      ...settingsRoutes("owner"),
      [create]: json(
        201,
        mode({ id: "mode-wave", name: "Wave", reference_required: true, display_order: 3 }),
      ),
    });
    await screen.findByRole("list", { name: LIST });
    expect(rowIn(LIST, "Orange Money").getByText("Référence demandée")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
    await user.type(screen.getByLabelText("Nom du mode"), "Wave");
    const reference = screen.getByRole("radiogroup", {
      name: "Référence de la transaction obligatoire",
    });
    await user.click(within(reference).getByRole("radio", { name: "Oui" }));
    await user.click(screen.getByRole("button", { name: "Ajouter le mode" }));
    expect(await screen.findByText("Wave")).toBeVisible();
    expect(bodyOf(fake.calls, create)).toMatchObject({
      name: "Wave",
      reference_required: true,
      display_order: 3,
    });
    expect(screen.getByLabelText("Nom du mode")).toHaveValue("");
  });

  it("renomme, demande la référence, désactive", async () => {
    const patch = route("PATCH", "/payment-modes/mode-cash");
    const { user, fake } = renderApp(viewPath("modes"), {
      ...settingsRoutes("owner"),
      [patch]: [
        json(200, mode({ name: "Cash", version: 2 })),
        json(200, mode({ name: "Cash", reference_required: true, version: 3 })),
        json(200, mode({ name: "Cash", reference_required: true, active: false, version: 4 })),
      ],
    });
    await screen.findByRole("list", { name: LIST });
    await user.click(rowIn(LIST, "Espèces").getByRole("button", { name: "Renommer" }));
    const field = screen.getByLabelText("Nouveau nom pour Espèces");
    await user.clear(field);
    await user.type(field, "Cash");
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByText("Cash")).toBeVisible();
    await user.click(rowIn(LIST, "Cash").getByRole("button", { name: "Demander la référence" }));
    expect(await rowIn(LIST, "Cash").findByText("Référence demandée")).toBeVisible();
    await user.click(rowIn(LIST, "Cash").getByRole("button", { name: "Désactiver" }));
    expect(await rowIn(LIST, "Cash").findByText("Désactivé")).toBeVisible();
    const bodies = fake.calls.filter((c) => `${c.method} ${c.url}` === patch).map((c) => c.body);
    expect(bodies).toEqual([
      { name: "Cash", version: 1 },
      { reference_required: true, version: 2 },
      { active: false, version: 3 },
    ]);
  });
});
