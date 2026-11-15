import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { axeViolations } from "../../testing/axe";
import { renderApp } from "../../testing/renderApp";
import {
  articleButton,
  money,
  NEW_SALE_PATH,
  plain,
  preloadSales,
  priceField,
  replaceText,
  sentSale,
  validateButton,
} from "../../testing/renderSale";
import type { SaleRole } from "../../testing/salesServer";
import { BAZIN, textileWorld, WX, type TextileArticle } from "../../testing/textileSale";

beforeAll(preloadSales);
beforeEach(() => {
  window.localStorage.clear();
  vi.spyOn(window, "print").mockImplementation(() => undefined);
});
afterEach(() => {
  vi.restoreAllMocks();
});

/** Le gérant voit le stock en mètres ; l'employé, une pastille seulement (2026-11-15). */
function renderTextile(articles: TextileArticle[] = [WX, BAZIN], role: SaleRole = "owner") {
  const world = textileWorld(role, articles);
  const view = renderApp(NEW_SALE_PATH, world.routes);
  return { ...view, ...world, recordSale: world.server.recordSale };
}

/** Nom exact, l'espace insécable de « 2,7 m » comprise. */
const nb = (text: string) => new RegExp(`^${text.replace(/[()]/g, "\\$&").replace(/ /g, "\\s")}$`);
const card = (name: string) => within(screen.getByRole("region", { name }));
const lengthField = () => priceField("Longueur");
const lineText = (name: string) =>
  plain(card(name).getByText("Ligne").closest("p")?.textContent ?? "");

describe("vente Textile au mètre / au rouleau (T41, design-system § 7.5, SCN-L3-02)", () => {
  it("TEX-01, TEX-04 : stock du gérant en mètres et rouleaux, raccourcis, 2,5 m à 2 500 ; axe", async () => {
    const { user, container, recordSale } = renderTextile();
    const list = await screen.findByRole("list", { name: /Les plus vendus|Articles trouvés/ });
    expect(plain(within(list).getByRole("button", { name: /Wax/ }).textContent)).toContain(
      "Stock à Boutique : 54,9 m",
    );
    await user.click(await articleButton("Wax Fleur de mariage"));
    const wax = card("Wax Fleur de mariage");
    expect(plain(wax.getByText(/Stock disponible/).textContent)).toBe(
      "Stock disponible à Boutique : 54,9 m (≈ 10 rouleaux)",
    );
    expect(wax.getByRole("radio", { name: "Au mètre" })).toHaveAttribute("aria-checked", "true");
    const shortcuts = wax.getByRole("radiogroup", { name: "Raccourcis" });
    expect(
      within(shortcuts)
        .getAllByRole("radio")
        .map((chip) => plain(chip.textContent)),
    ).toEqual(["Rouleau complet (5,49 m)", "Demi-rouleau (2,7 m)", "1 m", "2 m", "3 m"]);
    expect(plain(priceField("Prix au mètre").value)).toBe("2 500");

    await user.click(within(shortcuts).getByRole("radio", { name: nb("Demi-rouleau (2,7 m)") }));
    expect(lengthField().value).toBe("2,7");
    await replaceText(user, lengthField(), "2,55");
    expect(await wax.findByText("Une décimale au plus (ex. 2,5)")).toBeVisible();
    await replaceText(user, lengthField(), "2,5");
    expect(wax.queryByText("Une décimale au plus (ex. 2,5)")).toBeNull();
    expect(lineText("Wax Fleur de mariage")).toBe(`Ligne${money(6250)}`);
    await replaceText(user, priceField("Prix au mètre"), "2400"); // prix négocié
    expect(lineText("Wax Fleur de mariage")).toBe(`Ligne${money(6000)}`);
    expect(await axeViolations(container)).toEqual([]);

    await user.click(validateButton());
    await screen.findByRole("heading", { name: /V-000001/ });
    expect(sentSale(recordSale).lines).toEqual([
      expect.objectContaining({
        article_id: WX.id,
        sale_mode: "meter",
        quantity: "2.5",
        unit_price: 2400,
      }),
    ]);
    expect(plain(screen.getByText(/× 2\s400/).textContent)).toContain("2,5 m × 2 400");
  });

  it("TEX-03 : « Au rouleau » pré-remplit 13 000, 1 rouleau = 5,5 m ; reçu « 1 rouleau (5,49 m) »", async () => {
    const { user, container, recordSale } = renderTextile();
    await user.click(await articleButton("Wax Fleur de mariage"));
    const wax = card("Wax Fleur de mariage");
    expect(wax.getByRole("radiogroup", { name: "Vendre au mètre ou au rouleau" })).toBeVisible();
    await user.click(wax.getByRole("radio", { name: "Au rouleau" }));
    expect(plain(priceField("Prix du rouleau").value)).toBe("13 000");
    expect(plain(wax.getByText(/retirés du stock/).textContent)).toBe(
      "1 rouleau = 5,5 m retirés du stock",
    );
    expect(wax.queryByRole("radiogroup", { name: "Raccourcis" })).toBeNull();
    await user.click(wax.getByRole("button", { name: /plus un/ }));
    expect(plain(wax.getByText(/retirés du stock/).textContent)).toBe(
      "2 rouleaux = 11 m retirés du stock",
    );
    expect(lineText("Wax Fleur de mariage")).toBe(`Ligne${money(26_000)}`);
    await user.click(wax.getByRole("button", { name: /moins un/ }));
    expect(await axeViolations(container)).toEqual([]);
    // Retour au mètre : le prix au mètre revient (prix de base de l'unité choisie).
    await user.click(wax.getByRole("radio", { name: "Au mètre" }));
    expect(plain(priceField("Prix au mètre").value)).toBe("2 500");
    await user.click(wax.getByRole("radio", { name: nb("Rouleau complet (5,49 m)") }));
    expect(wax.getByRole("radio", { name: "Au rouleau" })).toHaveAttribute("aria-checked", "true");

    await user.click(validateButton());
    await screen.findByRole("heading", { name: /V-000001/ });
    expect(sentSale(recordSale).lines[0]).toMatchObject({
      sale_mode: "piece",
      quantity: "1",
      unit_price: 13_000,
    });
    await user.click(screen.getByRole("button", { name: "Imprimer" }));
    expect(plain((await screen.findByText(/1 rouleau \(5,49 m\)/)).textContent)).toBe(
      "1 rouleau (5,49 m) × 13 000 FCFA",
    );
  });

  it("vente jamais refusée : 2,9 m restants, 3 m puis 1 rouleau passent sans blocage", async () => {
    const { user, recordSale } = renderTextile([{ ...WX, stock: "2.9" }]);
    await user.click(await articleButton("Wax Fleur de mariage"));
    const wax = card("Wax Fleur de mariage");
    expect(plain(wax.getByText(/Stock disponible/).textContent)).toBe(
      "Stock disponible à Boutique : 2,9 m (≈ 0 rouleau)",
    );
    await user.click(wax.getByRole("radio", { name: "3 m" }));
    expect(wax.queryByText(/Stock insuffisant/)).toBeNull();
    await user.click(wax.getByRole("radio", { name: "Au rouleau" }));
    await user.click(wax.getByRole("button", { name: /plus un/ })); // pas de plafond au stock
    expect(wax.queryByText(/Stock insuffisant/)).toBeNull();
    await user.click(validateButton());
    await screen.findByRole("heading", { name: /V-000001/ });
    expect(sentSale(recordSale).lines[0]).toMatchObject({ sale_mode: "piece", quantity: "2" });
  });

  it("employé : pastille seule, aucun chiffre de stock, vente d'un article en rupture ; axe", async () => {
    const articles = [
      { ...WX, status: "out" as const },
      { ...BAZIN, status: "low" as const },
    ];
    const { user, container, recordSale } = renderTextile(articles, "seller");
    const list = await screen.findByRole("list", { name: /Les plus vendus|Articles trouvés/ });
    const wax = within(list).getByRole("button", { name: /Wax/ });
    expect(within(wax).getByText("Rupture")).toBeVisible();
    expect(within(list).getByText("Stock bas")).toBeVisible();
    expect(plain(list.textContent)).not.toMatch(/Stock à|\d+,\d m|54|12 m/);
    await user.click(wax); // rupture : la ligne s'ouvre quand même
    const line = card("Wax Fleur de mariage");
    expect(plain(line.getByText(/^Stock/).textContent)).toBe("Stock : Rupture");
    expect(line.queryByText(/Stock disponible|rouleaux\)/)).toBeNull();
    expect(plain(document.body.textContent)).not.toMatch(/54,9|54\.9|≈/);
    expect(screen.queryByText(/coût|marge|CMP/i)).toBeNull(); // TR-05
    expect(await axeViolations(container)).toEqual([]);
    await user.click(line.getByRole("radio", { name: "3 m" }));
    await user.click(validateButton());
    await screen.findByRole("heading", { name: /V-000001/ });
    expect(sentSale(recordSale).lines[0]).toMatchObject({ sale_mode: "meter", quantity: "3.0" });
  });

  it("article au mètre seulement : pas de bascule, rouleau sur 6 yards (5,5 m), demi 2,7 m", async () => {
    const { user, recordSale } = renderTextile([BAZIN]);
    await user.click(await articleButton("Bazin riche"));
    const bazin = card("Bazin riche");
    expect(bazin.queryByRole("radio", { name: "Au rouleau" })).toBeNull();
    expect(plain(bazin.getByText(/Stock disponible/).textContent)).toBe(
      "Stock disponible à Boutique : 12 m",
    );
    await user.click(bazin.getByRole("radio", { name: nb("Rouleau complet (5,5 m)") }));
    expect(lengthField().value).toBe("5,5");
    expect(bazin.getByRole("radio", { name: nb("Demi-rouleau (2,7 m)") })).toBeVisible();
    await user.click(validateButton());
    await screen.findByRole("heading", { name: /V-000001/ });
    expect(sentSale(recordSale).lines[0]).toMatchObject({ sale_mode: "meter", quantity: "5.5" });
  });

  it("longueur vide : « Indiquez la longueur » au premier appui, rien n'est envoyé", async () => {
    const { user, recordSale } = renderTextile([BAZIN], "seller");
    await user.click(await articleButton("Bazin riche"));
    await user.click(validateButton());
    expect(card("Bazin riche").getByText("Indiquez la longueur")).toBeVisible();
    expect(recordSale).not.toHaveBeenCalled();
  });
});
