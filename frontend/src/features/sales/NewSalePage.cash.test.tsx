import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { isUuidV7 } from "../../core/api/uuidv7";
import { axeViolations } from "../../testing/axe";
import {
  articleButton,
  gestureCounter,
  priceField,
  renderSale,
  replaceText,
  money,
  plain,
  validateButton,
} from "../../testing/renderSale";

beforeEach(() => {
  window.localStorage.clear();
});

const radio = (name: string) => screen.getByRole("radio", { name });

describe("Nouvelle vente au comptant (UC-VEN-01)", () => {
  it("les plus vendus sont proposés quand la recherche est vide, la rupture n'est pas choisissable", async () => {
    const { container } = renderSale();
    const list = await screen.findByRole("list", { name: "Les plus vendus" });
    const titles = within(list)
      .getAllByRole("listitem")
      .map((item) => item.textContent);
    expect(titles[0]).toMatch(/^Haojue HJ125-8/);
    expect(titles).toHaveLength(5);
    const rupture = within(list).getByText("Rupture");
    expect(rupture.closest("li")?.querySelector("button")).toBeNull();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("recherche dès la première lettre, sans accent ni casse", async () => {
    const { user } = renderSale();
    await screen.findByRole("list", { name: "Les plus vendus" });
    await user.type(screen.getByLabelText("Article"), "j");
    const list = await screen.findByRole("list", { name: "Articles trouvés" });
    expect(
      within(list)
        .getAllByRole("button")
        .map((b) => b.textContent),
    ).toEqual([
      expect.stringMatching(/^Haojue HJ125-8/),
      expect.stringMatching(/^Haojue HJ150-10/),
      expect.stringMatching(/^Jincheng JC125/),
    ]);
  });

  it("se fait en 4 gestes : article, prix, paiement, valider", async () => {
    const { user, recordSale, container } = renderSale();
    const gestures = gestureCounter();
    const article = await articleButton("Haojue HJ125-8");

    await gestures.run(() => user.click(article));
    expect(screen.getByText("Stock disponible à Garoua : 4")).toBeVisible();
    expect(plain(priceField().value)).toBe("780 000");
    expect(radio("Espèces")).toHaveAttribute("aria-checked", "true");
    expect(await axeViolations(container)).toEqual([]);

    await gestures.run(() => replaceText(user, priceField(), "750000"));
    await gestures.run(() => user.click(radio("Orange Money")));
    await gestures.run(() => user.click(validateButton()));

    expect(
      await screen.findByRole("heading", { name: "Vente enregistrée — reçu n° V-000124" }),
    ).toHaveFocus();
    expect(gestures.count).toBe(4);
    const [, command] = recordSale.mock.calls[0] ?? [];
    expect(command).toEqual({
      id: expect.any(String) as string,
      location_id: "loc-garoua",
      sold_on: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/) as string,
      kind: "cash",
      customer: null,
      lines: [
        {
          article_id: "art-hj125-8",
          sale_mode: "unit",
          quantity: "1",
          unit_price: 750_000,
          details: [],
        },
      ],
      payments: [{ mode_id: "pm-orange", amount: 750_000, reference: null }],
      credit: null,
      price_request_id: null,
      note: null,
    });
    expect(isUuidV7(command?.id ?? "")).toBe(true);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("confirmation : total, Imprimer et Partager à venir, puis « Nouvelle vente » avec le dernier mode", async () => {
    const { user } = renderSale();
    await user.click(await articleButton("Sanya SY125-8"));
    await user.click(radio("MTN MoMo"));
    await user.click(validateButton());
    await screen.findByRole("heading", { name: /V-000124/ });
    expect(screen.getAllByText(money(650_000)).length).toBeGreaterThan(0);
    for (const name of ["Imprimer", "Partager"]) {
      expect(screen.getByRole("button", { name })).toHaveAttribute("aria-disabled", "true");
    }
    expect(screen.getAllByText("Reçus : à venir")).toHaveLength(2);

    await user.click(screen.getByRole("button", { name: "Nouvelle vente" }));
    await user.click(await articleButton("Sanya SY125-8"));
    expect(screen.getByText("Stock disponible à Garoua : 6")).toBeVisible();
    expect(radio("MTN MoMo")).toHaveAttribute("aria-checked", "true");
    await user.click(validateButton());
    expect(await screen.findByRole("heading", { name: /V-000125/ })).toBeVisible();
  });

  it("plusieurs lignes, quantité bornée par le stock, détails par unité", async () => {
    const { user, recordSale } = renderSale();
    await user.click(await articleButton("Nanfang NF125-2"));
    const plus = screen.getByRole("button", { name: "Quantité : plus un" });
    expect(plus).toHaveAttribute("aria-disabled", "true");

    await user.click(screen.getByRole("button", { name: "Ajouter un article" }));
    await user.click(await articleButton("Haojue HJ125-8"));
    const line = screen.getByRole("region", { name: "Haojue HJ125-8" });
    await user.click(within(line).getByRole("button", { name: "Quantité : plus un" }));
    await user.click(within(line).getByRole("button", { name: /Plus de détails/ }));
    await user.type(within(line).getByLabelText("N° de châssis — moto 2"), "lbx0002");
    await user.type(within(line).getByLabelText("Couleur — moto 1"), "Rouge");

    expect(screen.getByText(money(620_000 + 2 * 780_000))).toBeVisible();
    await user.click(validateButton());
    await screen.findByRole("heading", { name: /V-000124/ });
    const [, command] = recordSale.mock.calls[0] ?? [];
    expect(command?.lines[1]).toMatchObject({
      quantity: "2",
      details: [
        { color: "Rouge", chassis_number: null, engine_number: null },
        { color: null, chassis_number: "LBX0002", engine_number: null },
      ],
    });
  });

  it("monnaie à rendre et montant remis insuffisant", async () => {
    const { user, recordSale } = renderSale();
    await user.click(await articleButton("Sanya SY125-8"));
    await user.click(screen.getByRole("button", { name: "Plus de détails" }));
    const given = priceField("Montant remis par le client");
    await user.type(given, "700000");
    expect(screen.getByText(money(50_000))).toBeVisible();
    await replaceText(user, given, "600000");
    await user.click(validateButton());
    expect(screen.getByText("Le montant remis est inférieur au total")).toBeVisible();
    expect(recordSale).not.toHaveBeenCalled();
  });
});
