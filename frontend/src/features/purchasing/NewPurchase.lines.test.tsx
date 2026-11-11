import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { formatMoney } from "../../shared/format";
import { axeViolations } from "../../testing/axe";
import { json } from "../../testing/fakeApi";
import {
  HAOJUE_ID,
  NOW,
  preloadPurchasing,
  purchase,
  PURCHASES_PATH,
  purchasingRoutes,
  route,
  setClock,
  WAX_ID,
  withArticleSearch,
  YAMAHA_ID,
} from "../../testing/purchasing";
import { chooseArticle, fillLine, lineGroup, sent, summaryValue } from "../../testing/purchasingUi";
import { renderApp } from "../../testing/renderApp";
import { money } from "../../testing/renderSale";

const NEW_PATH = `${PURCHASES_PATH}?vue=nouvel`;
const POST = route("POST", "/purchases");

beforeAll(preloadPurchasing);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

function open() {
  return renderApp(
    NEW_PATH,
    withArticleSearch(purchasingRoutes("accountant", { [POST]: json(201, purchase()) })),
  );
}

describe("plusieurs lignes et frais répartis au prorata (RG-T10)", () => {
  it("le reste d'arrondi va à la ligne de plus forte valeur, comme le serveur", async () => {
    const { user, fake, container } = open();
    await screen.findByRole("heading", { name: "Nouvel achat" });
    await chooseArticle(user, "hao", "Haojue HJ125-8");
    await fillLine(user, "2", "500000");
    await user.click(screen.getByRole("button", { name: "Ajouter une ligne" }));
    await chooseArticle(user, "yam", "Yamaha YBR125", 2);
    await fillLine(user, "1", "300000", 2);
    expect(lineGroup(2)).toHaveTextContent(`Total de la ligne${money(300000)}`);
    await user.click(screen.getByRole("button", { name: "Plus de détails" }));
    await user.click(screen.getByRole("button", { name: "Ajouter : Transport" }));
    await user.type(screen.getByLabelText("Frais : Transport"), "100001");
    // 100 001 : 76 923 + 23 077 = 100 000, le franc restant va à Haojue (1 000 000 FCFA).
    expect(summaryValue("Coût unitaire final — Haojue HJ125-8")).toBe(
      `${formatMoney(538462)} par unité`,
    );
    expect(summaryValue("Coût unitaire final — Yamaha YBR125")).toBe(
      `${formatMoney(323077)} par unité`,
    );
    expect(summaryValue("Total de l'achat")).toBe(formatMoney(1400001));
    expect(await axeViolations(container)).toEqual([]);

    await user.click(screen.getByRole("button", { name: "Valider l'achat" }));
    await screen.findByRole("heading", { name: "Achat enregistré — A-000012" });
    expect(sent(fake.calls, "POST", "/purchases")).toMatchObject({
      lines: [
        { article_id: HAOJUE_ID, quantity: "2", unit: "UNIT", unit_price: 500000 },
        { article_id: YAMAHA_ID, quantity: "1", unit: "UNIT", unit_price: 300000 },
      ],
      fees: [{ kind: "transport", amount: 100001, label: null }],
    });
  });

  it("frais « Autre » : libellé exigé ; une ligne se retire ; un article ne figure qu'une fois", async () => {
    const { user, fake } = open();
    await screen.findByRole("heading", { name: "Nouvel achat" });
    await chooseArticle(user, "hao", "Haojue HJ125-8");
    await fillLine(user, "1", "500000");
    await user.click(screen.getByRole("button", { name: "Ajouter une ligne" }));
    await chooseArticle(user, "hao", "Haojue HJ125-8", 2);
    await fillLine(user, "1", "500000", 2);
    await user.click(screen.getByRole("button", { name: "Plus de détails" }));
    await user.click(screen.getByRole("button", { name: "Ajouter : Autre" }));
    await user.type(screen.getByLabelText("Frais : Autre"), "5000");
    await user.click(screen.getByRole("button", { name: "Valider l'achat" }));
    expect(screen.getByText("Les frais « Autre » exigent un libellé")).toBeVisible();
    expect(
      within(lineGroup(2)).getByText("Cet article figure déjà sur une autre ligne"),
    ).toBeVisible();
    expect(fake.count(POST)).toBe(0);

    await user.type(screen.getByLabelText("Libellé des frais"), "Gardiennage");
    await user.click(screen.getByRole("button", { name: "Retirer la ligne 2" }));
    await user.click(screen.getByRole("button", { name: "Valider l'achat" }));
    await screen.findByRole("heading", { name: "Achat enregistré — A-000012" });
    expect(sent(fake.calls, "POST", "/purchases")).toMatchObject({
      fees: [{ kind: "other", amount: 5000, label: "Gardiennage" }],
    });
  });
});

describe("unité saisie (RG-X02) : tissu au mètre, en yards ou à la pièce", () => {
  it("10 yards à 3 000 FCFA → 9,1 m en stock, coût final au mètre", async () => {
    const { user, fake } = open();
    await screen.findByRole("heading", { name: "Nouvel achat" });
    await chooseArticle(user, "wax", "Wax hollandais");
    const line = lineGroup(1);
    const units = within(line).getByRole("radiogroup", { name: "Unité saisie" });
    expect(
      within(units)
        .getAllByRole("radio")
        .map((r) => r.textContent),
    ).toEqual(["Mètre", "Yard", "Pièce"]);
    expect(within(units).getByRole("radio", { name: "Mètre" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    await user.click(within(units).getByRole("radio", { name: "Yard" }));
    expect(within(line).getByText("Convertie en mètres (1 yard = 0,9144 m)")).toBeVisible();
    await user.type(within(line).getByLabelText("Quantité"), "10");
    await user.type(within(line).getByLabelText("Prix unitaire (par yard)"), "3000");
    expect(line).toHaveTextContent(`Total de la ligne${money(30000)}`);
    // 30 000 / 9,1 m = 3 296,7 → 3 297 FCFA le mètre.
    expect(summaryValue("Coût unitaire final — Wax hollandais")).toBe(
      `${formatMoney(3297)} par mètre`,
    );
    await user.click(screen.getByRole("button", { name: "Valider l'achat" }));
    await screen.findByRole("heading", { name: "Achat enregistré — A-000012" });
    expect(sent(fake.calls, "POST", "/purchases")).toMatchObject({
      lines: [{ article_id: WAX_ID, quantity: "10", unit: "YARD", unit_price: 3000 }],
    });
  });

  it("au mètre : un dixième au plus ; à la pièce : pièces x longueur (5,5 m)", async () => {
    const { user } = open();
    await screen.findByRole("heading", { name: "Nouvel achat" });
    await chooseArticle(user, "wax", "Wax hollandais");
    const line = lineGroup(1);
    await user.type(within(line).getByLabelText("Quantité"), "2,55");
    await user.type(within(line).getByLabelText("Prix unitaire (par mètre)"), "4000");
    await user.click(screen.getByRole("button", { name: "Valider l'achat" }));
    expect(within(line).getByText("Un chiffre après la virgule au plus")).toBeVisible();

    await user.click(within(line).getByRole("radio", { name: "Pièce" }));
    await user.clear(within(line).getByLabelText("Quantité"));
    await user.type(within(line).getByLabelText("Quantité"), "2");
    // 2 pièces x 4 000 = 8 000 FCFA pour 11 m → 727,27 → 727 FCFA le mètre.
    expect(summaryValue("Coût unitaire final — Wax hollandais")).toBe(
      `${formatMoney(727)} par mètre`,
    );
  });
});
