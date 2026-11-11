import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { axeViolations } from "../../testing/axe";
import { apiError, json } from "../../testing/fakeApi";
import {
  NOW,
  page,
  preloadPurchasing,
  purchase,
  PURCHASES_PATH,
  purchasingRoutes,
  route,
  setClock,
  supplier,
} from "../../testing/purchasing";
import { sent } from "../../testing/purchasingUi";
import { renderApp } from "../../testing/renderApp";
import { money } from "../../testing/renderSale";
import { NAME_EMPTY } from "./SupplierForm";

const LIST = `${PURCHASES_PATH}?vue=fournisseurs`;
const SHEET = route("GET", "/suppliers/sup-1");
const PATCH = route("PATCH", "/suppliers/sup-1");

function sheet(overrides = {}) {
  const { items, totals } = page([purchase()]);
  return {
    supplier: supplier(overrides),
    first_day: "2026-11-01",
    last_day: "2026-11-30",
    totals,
    purchases: items,
  };
}

beforeAll(preloadPurchasing);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

describe("fournisseurs (UC-ACH-02)", () => {
  it("liste (désactivés signalés), création avec détails, puis fiche", async () => {
    const created = supplier({ id: "sup-1", name: "Motos Sahel", phone: "+237690000000" });
    const { user, fake, container } = renderApp(
      LIST,
      purchasingRoutes("accountant", {
        [route("POST", "/suppliers")]: json(201, created),
        [SHEET]: json(200, sheet({ name: "Motos Sahel" })),
      }),
    );
    const list = await screen.findByRole("list", { name: "Liste des fournisseurs" });
    expect(
      within(list)
        .getAllByRole("button")
        .map((b) => b.textContent),
    ).toEqual(["Haojue DoualaDouala · Cameroun", "Ancien ImportCamerounDésactivé"]);
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Nouveau fournisseur" }));
    await user.click(await screen.findByRole("button", { name: "Créer le fournisseur" }));
    expect(screen.getByText(NAME_EMPTY)).toBeVisible();
    await user.type(screen.getByLabelText("Nom du fournisseur"), "Motos Sahel");
    await user.click(screen.getByRole("button", { name: "Plus de détails" }));
    await user.type(screen.getByLabelText("Téléphone"), "+237690000000");
    await user.click(screen.getByRole("button", { name: "Créer le fournisseur" }));
    expect(await screen.findByText("Fournisseur créé : Motos Sahel")).toBeVisible();
    const body = sent(fake.calls, "POST", "/suppliers") as { id: string };
    expect(body).toEqual({
      id: body.id,
      name: "Motos Sahel",
      phone: "+237690000000",
      city: null,
      country: null,
      note: null,
    });
    expect(await screen.findByRole("heading", { name: "Motos Sahel" })).toBeVisible();
  });

  it("nom déjà pris : refus clair", async () => {
    const { user } = renderApp(
      `${PURCHASES_PATH}?vue=fournisseur-nouveau`,
      purchasingRoutes("owner", {
        [route("POST", "/suppliers")]: apiError(409, "DUPLICATE", "Pris"),
      }),
    );
    await user.type(await screen.findByLabelText("Nom du fournisseur"), "Haojue Douala");
    await user.click(screen.getByRole("button", { name: "Créer le fournisseur" }));
    expect(await screen.findByText(/porte déjà ce nom/)).toBeVisible();
  });

  it("fiche : total acheté sur la période et ses achats ; période modifiable", async () => {
    const { user, fake } = renderApp(
      `${PURCHASES_PATH}?vue=fournisseur&id=sup-1`,
      purchasingRoutes("accountant", {
        [SHEET]: json(200, sheet()),
        [route("GET", "/suppliers/sup-1?from=2026-11-05&to=2026-11-11")]: json(200, {
          ...sheet(),
          purchases: [],
          totals: { count: 0, merchandise: 0, fees: 0, total: 0, paid: 0 },
        }),
      }),
    );
    expect(await screen.findByText("Total acheté du 01/11/2026 au 30/11/2026")).toBeVisible();
    const kpi = screen.getByText("Total acheté du 01/11/2026 au 30/11/2026").parentElement;
    expect(kpi).toHaveTextContent(`${money(10800000).replace(" FCFA", "")}FCFA1 achat`);
    expect(screen.getByRole("list", { name: "Achats chez Haojue Douala" })).toHaveTextContent(
      "A-000012",
    );
    await user.click(screen.getByRole("radio", { name: "7 derniers jours" }));
    expect(
      await screen.findByText("Aucun achat chez ce fournisseur sur cette période."),
    ).toBeVisible();
    expect(fake.count(route("GET", "/suppliers/sup-1?from=2026-11-05&to=2026-11-11"))).toBe(1);
  });

  it("modifier (champs changés + version), désactiver avec confirmation, réactiver", async () => {
    const { user, fake } = renderApp(
      `${PURCHASES_PATH}?vue=fournisseur&id=sup-1`,
      purchasingRoutes("owner", {
        [SHEET]: json(200, sheet()),
        [PATCH]: [
          json(200, supplier({ city: "Garoua", version: 2 })),
          json(200, supplier({ city: "Garoua", version: 3, active: false })),
          json(200, supplier({ city: "Garoua", version: 4 })),
        ],
      }),
    );
    await user.click(await screen.findByRole("button", { name: "Modifier le fournisseur" }));
    const city = await screen.findByLabelText("Ville");
    await user.clear(city);
    await user.type(city, "Garoua");
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(await screen.findByText("Fournisseur modifié : Haojue Douala")).toBeVisible();
    expect(sent(fake.calls, "PATCH", "/suppliers/sup-1", 0)).toEqual({
      version: 1,
      city: "Garoua",
    });

    await user.click(await screen.findByRole("button", { name: "Désactiver le fournisseur" }));
    const dialog = screen.getByRole("dialog", { name: "Désactiver Haojue Douala ?" });
    await user.click(within(dialog).getByRole("button", { name: "Désactiver" }));
    expect(await screen.findByText("Désactivé")).toBeVisible();
    expect(sent(fake.calls, "PATCH", "/suppliers/sup-1", 1)).toEqual({ version: 2, active: false });
    await user.click(screen.getByRole("button", { name: "Réactiver le fournisseur" }));
    expect(await screen.findByRole("button", { name: "Désactiver le fournisseur" })).toBeVisible();
    expect(sent(fake.calls, "PATCH", "/suppliers/sup-1", 2)).toEqual({ version: 3, active: true });
  });
});
