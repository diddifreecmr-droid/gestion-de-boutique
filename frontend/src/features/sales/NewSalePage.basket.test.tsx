import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { BOULAI, GAROUA, NGAOUNDERE } from "../../core/gateways/simulated/seed";
import { axeViolations } from "../../testing/axe";
import { json } from "../../testing/fakeApi";
import {
  articleButton,
  money,
  plain,
  preloadSales,
  priceField,
  renderSale,
  replaceText,
  sentSale,
  validateButton,
} from "../../testing/renderSale";
import { apparelSaleProfile } from "../../testing/salesCatalog";
import { API } from "../../testing/salesServer";

beforeAll(preloadSales);
beforeEach(() => {
  window.localStorage.clear();
  vi.spyOn(window, "print").mockImplementation(() => undefined);
});
afterEach(() => {
  vi.restoreAllMocks();
});

const stock = (garoua: number) => ({ [GAROUA.id]: garoua, [NGAOUNDERE.id]: 0, [BOULAI.id]: 0 });
const CHEMISE = {
  id: "art-chemise",
  name: "Chemise lin",
  base_price: 15_000,
  min_price: 12_000,
  min_price_shared: true,
  rank: 1,
  stock: stock(5),
};
const BASKETS = {
  id: "art-baskets",
  name: "Baskets toile",
  base_price: 17_500,
  min_price: 15_000,
  min_price_shared: false, // minimum tu au vendeur : rien n'est montré
  rank: 2,
  stock: stock(2),
};

function renderApparel() {
  const view = renderSale("seller", {
    extra: { [`GET ${API}/profile`]: json(200, apparelSaleProfile("seller")) },
  });
  view.server.world.articles.set(CHEMISE.id, CHEMISE);
  view.server.world.articles.set(BASKETS.id, BASKETS);
  return view;
}

const card = (name: string) => within(screen.getByRole("region", { name }));
const total = () => plain(screen.getByText(/Total$/).closest("p")?.textContent ?? "");

describe("vente Prêt-à-porter simplifiée (2026-11-15, design-system § 7.4)", () => {
  it("PAN-03 : liste d'articles, quantité, prix négocié, total ; ni taille ni couleur ; axe", async () => {
    const { user, container, recordSale } = renderApparel();
    await user.click(await articleButton("Chemise lin"));
    const chemise = card("Chemise lin");
    expect(chemise.queryByRole("radiogroup", { name: /Taille|Couleur/ })).toBeNull();
    expect(plain(priceField("Prix unitaire").value)).toBe("15 000");
    expect(chemise.getByLabelText("Prix unitaire")).toHaveAccessibleDescription(
      /^Base 15\s000\sFCFA · minimum 12\s000\sFCFA/,
    );
    await user.click(chemise.getByRole("button", { name: /plus un/ }));
    await replaceText(user, priceField("Prix unitaire"), "14000");
    expect(plain(chemise.getByText("Ligne").closest("p")?.textContent ?? "")).toBe(
      `Ligne${money(28_000)}`,
    );
    expect(total()).toBe(`Total${money(28_000)}`);

    await user.click(screen.getByRole("button", { name: "Ajouter un article" }));
    await user.click(await articleButton("Baskets toile"));
    // Les deux lignes restent ouvertes : article, quantité, prix.
    expect(card("Chemise lin").getByLabelText("Prix unitaire")).toBeVisible();
    expect(card("Baskets toile").queryByRole("radio")).toBeNull();
    expect(total()).toBe(`2 articles · Total${money(45_500)}`);
    expect(container.textContent).not.toMatch(/remise|sous-total/i);
    expect(screen.getByRole("radio", { name: /Espèces/ })).toBeChecked();
    expect(await axeViolations(container)).toEqual([]);

    await user.click(validateButton());
    expect(await screen.findByRole("heading", { name: /V-000124/ })).toBeVisible();
    const sent = sentSale(recordSale);
    expect(sent.lines).toEqual([
      expect.objectContaining({
        article_id: CHEMISE.id,
        quantity: "2",
        unit_price: 14_000,
        details: [],
      }),
      expect.objectContaining({
        article_id: BASKETS.id,
        quantity: "1",
        unit_price: 17_500,
        details: [],
      }),
    ]);
    expect(JSON.stringify(sent)).not.toMatch(/discount|gross_total|size|"color"/);

    // PAN-02 : reçu ligne par ligne (quantité × prix), puis le total.
    await user.click(screen.getByRole("button", { name: "Imprimer" }));
    const receipt = plain((await screen.findByRole("article", { name: "Reçu" })).textContent);
    expect(receipt).toContain(`2 × ${money(14_000)}${money(28_000)}`);
    expect(receipt).toContain(`Total${money(45_500)}`);
    expect(receipt).not.toMatch(/remise|coût|marge|Taille/i);
  });

  it("employé : pastilles sans chiffre, rupture vendable au-delà du stock, article non reproposé", async () => {
    const { user, container } = renderApparel();
    const list = await screen.findByRole("list", { name: /Les plus vendus/ });
    const row = (name: RegExp) => within(within(list).getByRole("button", { name }));
    expect(row(/Chemise/).getByText("En stock")).toBeVisible(); // Chemise : 5
    expect(row(/Baskets/).getByText("Stock bas")).toBeVisible(); // Baskets : 2
    expect(plain(list.textContent)).not.toMatch(/Stock à|: \d/);
    await user.click(await articleButton("Baskets toile"));
    const baskets = card("Baskets toile");
    const stockLine = baskets.getByText("Stock bas").closest("p");
    expect(plain(stockLine?.textContent ?? "")).toBe("Stock : Stock bas");
    for (let n = 0; n < 4; n += 1) {
      await user.click(baskets.getByRole("button", { name: /plus un/ })); // jamais bloqué au stock
    }
    expect(baskets.getByRole("button", { name: /plus un/ })).toBeEnabled();
    expect(plain(container.textContent)).not.toMatch(/Stock insuffisant|disponible à/);
    await user.click(screen.getByRole("button", { name: "Ajouter un article" }));
    const again = await screen.findByRole("list", { name: /Les plus vendus/ });
    expect(within(again).queryByRole("button", { name: /Baskets/ })).toBeNull();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("sous le minimum : avertissement sous le prix, la vente reste possible", async () => {
    const { user } = renderApparel();
    await user.click(await articleButton("Chemise lin"));
    await replaceText(user, priceField("Prix unitaire"), "11000");
    expect(plain(screen.getByText(/Sous le prix minimum/).textContent)).toBe(
      `Sous le prix minimum (${money(12_000)}) : la vente sera notée au journal`,
    );
    expect(validateButton()).not.toHaveAttribute("aria-disabled");
  });
});
