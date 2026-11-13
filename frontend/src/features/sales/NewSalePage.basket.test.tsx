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

describe("panier multi-lignes Prêt-à-porter (T40, design-system § 7.4)", () => {
  it("PAN-03 : taille, couleur, prix négocié par ligne, total recalculé, aucune remise ; axe", async () => {
    const { user, container, recordSale } = renderApparel();
    await user.click(await articleButton("Chemise lin"));
    const chemise = card("Chemise lin");
    expect(chemise.getByRole("radiogroup", { name: "Taille" })).toBeVisible();
    await user.click(chemise.getByRole("radio", { name: "M" }));
    await user.click(chemise.getByRole("radio", { name: "Blanc" }));
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
    // La première ligne se replie ; la nouvelle est ouverte, en pointures.
    expect(screen.queryByRole("region", { name: "Chemise lin" })).toBeNull();
    const folded = screen.getByRole("list", { name: "Ligne repliée : Chemise lin" });
    expect(plain(folded.textContent)).toContain(`T. M · Blanc — 2 × ${money(14_000)}`);
    const baskets = card("Baskets toile");
    expect(baskets.queryByRole("radio", { name: "M" })).toBeNull();
    await user.click(baskets.getByRole("radio", { name: "42" }));
    const colors = within(baskets.getByRole("radiogroup", { name: "Couleur" }));
    await user.click(colors.getByRole("radio", { name: "Autre" }));
    await user.type(baskets.getByLabelText("Autre couleur"), "Kaki");
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
        details: [{ size: "M", color: "Blanc" }],
      }),
      expect.objectContaining({
        article_id: BASKETS.id,
        quantity: "1",
        unit_price: 17_500,
        details: [{ size: "42", color: "Kaki" }],
      }),
    ]);
    expect(JSON.stringify(sent)).not.toMatch(/discount|gross_total/);

    // PAN-02 : reçu ligne par ligne (taille, couleur, quantité × prix), puis le total.
    await user.click(screen.getByRole("button", { name: "Imprimer" }));
    const receipt = plain((await screen.findByRole("article", { name: "Reçu" })).textContent);
    expect(receipt).toContain(`Couleur : Blanc · Taille : M2 × ${money(14_000)}${money(28_000)}`);
    expect(receipt).toContain(`Couleur : Kaki · Taille : 421 × ${money(17_500)}`);
    expect(receipt).toContain(`Total${money(45_500)}`);
    expect(receipt).not.toMatch(/remise|coût|marge/i);
  });

  it("même article en deux tailles ; une ligne repliée se rouvre ; stock partagé", async () => {
    const { user } = renderApparel();
    await user.click(await articleButton("Chemise lin"));
    await user.click(card("Chemise lin").getByRole("radio", { name: "M" }));
    await user.click(screen.getByRole("button", { name: "Ajouter un article" }));
    await user.click(await articleButton("Chemise lin"));
    const open = card("Chemise lin");
    await user.click(open.getByRole("radio", { name: "L" }));
    const folded = screen.getByRole("list", { name: "Ligne repliée : Chemise lin" });
    expect(plain(folded.textContent)).toContain("T. M");
    await user.click(within(folded).getByRole("button"));
    expect(card("Chemise lin").getByRole("radio", { name: "M" })).toBeChecked();
    expect(plain(screen.getByRole("list", { name: /Ligne repliée/ }).textContent)).toContain(
      "T. L",
    );
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
