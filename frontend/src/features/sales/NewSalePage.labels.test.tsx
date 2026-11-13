import { screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { GAROUA, NGAOUNDERE, BOULAI } from "../../core/gateways/simulated/seed";
import { axeViolations } from "../../testing/axe";
import { API } from "../../testing/salesServer";
import { json } from "../../testing/fakeApi";
import { renderSale, preloadSales, validateButton } from "../../testing/renderSale";
import { apparelSaleProfile } from "../../testing/salesCatalog";

beforeAll(preloadSales);
beforeEach(() => {
  window.localStorage.clear();
});

const ROBE = {
  id: "art-robe",
  name: "Robe Bleu Marine Robe",
  base_price: 15_000,
  min_price: 10_000,
  min_price_shared: false,
  rank: 1,
  stock: { [GAROUA.id]: 3, [NGAOUNDERE.id]: 0, [BOULAI.id]: 0 },
};

describe("Nouvelle vente : libellés et ordre (audit UX du 13/11/2026)", () => {
  it("Motos : la recherche parle de marque et de modèle", async () => {
    renderSale();
    expect(await screen.findByLabelText("Article")).toHaveAccessibleDescription(
      "Cherchez par marque ou modèle",
    );
  });

  it("Prêt-à-porter : libellés du profil, jamais « modèle » ; titre sans mot répété", async () => {
    const view = renderSale("seller", {
      extra: { [`GET ${API}/profile`]: json(200, apparelSaleProfile("seller")) },
    });
    view.server.world.articles.set(ROBE.id, ROBE);
    const field = await screen.findByLabelText("Article");
    expect(field).toHaveAccessibleDescription("Cherchez par nom, référence ou marque");
    const list = await screen.findByRole("list", { name: "Les plus vendus" });
    const robe = within(list).getByRole("button", { name: /^Robe Bleu Marine/ });
    expect(robe.textContent).not.toMatch(/Marine Robe/);
    await view.user.click(robe);
    expect(screen.getByRole("heading", { name: "Robe Bleu Marine" })).toBeVisible();
    expect(view.container.textContent).not.toMatch(/modèle/i);
    expect(validateButton()).toBeVisible();
    expect(await axeViolations(view.container)).toEqual([]);
  });

  it("les ruptures sont proposées après les articles en stock, marquées « Rupture »", async () => {
    renderSale();
    const list = await screen.findByRole("list", { name: "Les plus vendus" });
    const rows = within(list).getAllByRole("listitem");
    const firstRupture = rows.findIndex((row) => within(row).queryByText("Rupture") !== null);
    expect(firstRupture).toBeGreaterThan(0);
    for (const row of rows.slice(firstRupture)) {
      expect(within(row).getByText("Rupture")).toBeVisible();
      expect(row.querySelector("button")).toBeNull();
    }
    for (const row of rows.slice(0, firstRupture)) {
      expect(row.querySelector("button")).not.toBeNull();
    }
  });
});
