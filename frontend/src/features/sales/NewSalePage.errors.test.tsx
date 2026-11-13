import { screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import {
  articleButton,
  plain,
  priceField,
  renderSale,
  replaceText,
  SALE_SHOP,
  validateButton,
  preloadSales,
  saleAlert,
} from "../../testing/renderSale";
import { OFFLINE_MESSAGE } from "./saleErrorMessage";
import { BELOW_MINIMUM } from "./useSaleSubmit";

beforeAll(preloadSales);
beforeEach(() => {
  window.localStorage.clear();
});

const ASK = "Demander l'accord du propriétaire";

describe("prix sous le minimum (UC-VEN-03)", () => {
  it("vendeur : « Valider » devient « Demander l'accord du propriétaire », puis en attente", async () => {
    const { user, recordSale, requestPriceApproval, container } = renderSale("seller", {
      priceApproval: true,
    });
    await user.click(await articleButton("Haojue HJ125-8"));
    await replaceText(user, priceField(), "700000");
    expect(screen.getByText(/Prix inférieur au minimum \(720 000 FCFA\)/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "Valider la vente" })).toBeNull();
    expect(await axeViolations(container)).toEqual([]);

    await user.click(screen.getByRole("button", { name: ASK }));
    expect(await screen.findByText("En attente")).toBeVisible();
    expect(validateButton()).toHaveAttribute("aria-disabled", "true");
    expect(
      screen.getByText(/En attente de l'accord du propriétaire — expire dans \d+ min/),
    ).toBeVisible();
    expect(requestPriceApproval).toHaveBeenCalledWith(SALE_SHOP, {
      id: expect.any(String) as string,
      article_id: "art-hj125-8",
      requested_price: 700_000,
      sale_mode: "unit",
    });
    await user.click(validateButton());
    expect(recordSale).not.toHaveBeenCalled();
    expect(await axeViolations(container)).toEqual([]);

    await replaceText(user, priceField(), "730000");
    expect(validateButton()).not.toHaveAttribute("aria-disabled");
  });

  it("propriétaire : vend librement sous le minimum", async () => {
    const { user } = renderSale("owner");
    await user.click(await articleButton("Haojue HJ125-8"));
    await replaceText(user, priceField(), "700000");
    expect(screen.queryByRole("button", { name: ASK })).toBeNull();
    await user.click(validateButton());
    expect(await screen.findByRole("heading", { name: /V-000124/ })).toBeVisible();
  });

  it("minimum tu par le catalogue : le serveur refuse, le bouton bascule", async () => {
    const { user } = renderSale("seller", { priceApproval: true });
    await user.click(await articleButton("Sanya SY150-3"));
    await replaceText(user, priceField(), "650000");
    await user.click(validateButton());
    expect(await saleAlert()).toHaveTextContent(BELOW_MINIMUM);
    expect(screen.getByRole("button", { name: ASK })).toBeVisible();
    expect(screen.getByText(/Prix inférieur au minimum \(680 000 FCFA\)/)).toBeVisible();
  });
});

describe("refus du serveur", () => {
  it("stock insuffisant : stock disponible et autres lieux, saisie conservée", async () => {
    const { user, container } = renderSale();
    await screen.findByRole("list", { name: "Les plus vendus" });
    await user.type(screen.getByLabelText("Article"), "hj150");
    await user.click(await articleButton("Haojue HJ150-10"));
    await user.click(screen.getByRole("button", { name: "Quantité : plus un" }));
    await user.click(validateButton());
    const alert = await saleAlert();
    expect(plain(alert.textContent)).toContain(
      "Stock insuffisant pour Haojue HJ150-10 : 1 disponible à Garoua. Autres lieux — Ngaoundéré : 3.",
    );
    const line = screen.getByRole("region", { name: "Haojue HJ150-10" });
    expect(within(line).getByRole("status")).toHaveTextContent("2");
    expect(await axeViolations(container)).toEqual([]);
  });

  it("châssis déjà vendu (RG-M01) : la vente concernée est citée", async () => {
    const { user } = renderSale();
    await user.click(await articleButton("Haojue HJ125-8"));
    await user.click(screen.getByRole("button", { name: "Détails de l'article" }));
    await user.type(screen.getByLabelText("N° de châssis — moto 1"), "lbxpcj0a1n0001234");
    await user.click(validateButton());
    expect(await saleAlert()).toHaveTextContent(
      "Le numéro de châssis LBXPCJ0A1N0001234 a déjà été vendu (vente V-000098).",
    );
  });

  it("hors connexion : message clair, saisie conservée, renvoi en un appui (même id)", async () => {
    const { user, network, fake, container } = renderSale();
    await user.click(await articleButton("Haojue HJ125-8"));
    await replaceText(user, priceField(), "760000");
    network.online = false;
    await user.click(validateButton());
    expect(await saleAlert()).toHaveTextContent(OFFLINE_MESSAGE);
    expect(plain(priceField().value)).toBe("760 000");
    expect(await axeViolations(container)).toEqual([]);

    network.online = true;
    await user.click(validateButton());
    expect(await screen.findByRole("heading", { name: /V-000124/ })).toBeVisible();
    const posts = fake.calls.filter((c) => c.method === "POST" && c.url.endsWith("/sales"));
    expect(posts).toHaveLength(2);
    const ids = posts.map((c) => (c.body as { id: string }).id);
    expect(ids[0]).toBe(ids[1]);
  });

  it("hors connexion à l'ouverture : « Réessayer »", async () => {
    const { user, network } = renderSale("seller", { online: false });
    expect(await screen.findByText("Connexion nécessaire pour ouvrir une vente.")).toBeVisible();
    network.online = true;
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("list", { name: "Les plus vendus" })).toBeVisible();
  });
});

describe("lignes et détails facultatifs", () => {
  it("retirer une ligne, fermer la recherche, référence et note envoyées", async () => {
    const { user, recordSale } = renderSale();
    await user.click(await articleButton("Haojue HJ125-8"));
    await user.click(screen.getByRole("button", { name: "Ajouter un article" }));
    await user.click(screen.getByRole("button", { name: "Fermer la recherche" }));
    await user.click(screen.getByRole("button", { name: "Ajouter un article" }));
    await user.click(await articleButton("Sanya SY125-8"));
    await user.click(screen.getByRole("button", { name: "Retirer Haojue HJ125-8" }));
    expect(screen.queryByRole("region", { name: "Haojue HJ125-8" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Plus de détails" }));
    await user.type(screen.getByLabelText("Référence du paiement"), "OM-7781");
    await user.type(screen.getByLabelText("Note"), "Livraison demain");
    await user.click(validateButton());
    await screen.findByRole("heading", { name: /V-000124/ });
    const [, command] = recordSale.mock.calls[0] ?? [];
    expect(command).toMatchObject({
      lines: [{ article_id: "art-sy125-8" }],
      payments: [{ mode_id: "pm-cash", amount: 650_000, reference: "OM-7781" }],
      note: "Livraison demain",
    });
  });
});

describe("TR-05 : le vendeur ne voit jamais de coût", () => {
  it("le catalogue n'envoie ni coût, ni CMP, ni marge ; l'écran n'en parle pas", async () => {
    const { gateways, user, container } = renderSale();
    const { items } = await gateways.catalog.searchArticles(SALE_SHOP, {
      location_id: "loc-garoua",
      query: "",
      limit: 20,
    });
    const keys = new Set(items.flatMap((item) => Object.keys(item)));
    expect([...keys].filter((key) => /cost|wac|margin|value/i.test(key))).toEqual([]);
    await user.click(await articleButton("Haojue HJ125-8"));
    await user.click(validateButton());
    await screen.findByRole("heading", { name: /V-000124/ });
    expect(container.textContent).not.toMatch(/coût|marge|CMP/i);
  });
});
