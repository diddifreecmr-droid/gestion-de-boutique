import { screen, within } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import { apiError, json } from "../../testing/fakeApi";
import {
  ADMIN_SHOP_ID,
  adminSession,
  PLATFORM,
  preloadLot1Screens,
  shopAccess,
  shopSummary,
} from "../../testing/lot1Screens";
import { renderApp } from "../../testing/renderApp";
import { blockingList } from "./profileBlocking";

beforeAll(preloadLot1Screens);

const ONE = `${PLATFORM}/${ADMIN_SHOP_ID}`;
const SHEET_PATH = `/plateforme?id=${ADMIN_SHOP_ID}`;
const sheetRoutes = () => ({
  ...adminSession(),
  [`GET ${ONE}`]: json(200, shopSummary()),
  [`GET ${ONE}/access`]: json(200, shopAccess()),
});

async function fillShop(user: ReturnType<typeof renderApp>["user"]) {
  await user.type(await screen.findByLabelText(/Nom de la boutique/), "Tissus Ngaoundéré");
  await user.type(screen.getByLabelText(/^Ville/), "Ngaoundéré");
  await user.type(screen.getByLabelText(/Téléphone de la boutique/), "222000000");
  await user.type(screen.getByLabelText(/Nom du propriétaire/), "Aïssatou");
  await user.type(screen.getByLabelText(/Téléphone du propriétaire/), "690000078");
}

describe("Console : type de boutique (T38, QC-1)", () => {
  it("PRF-05 : les 3 types sont proposés, aucun d'avance ; Textile envoie profile_code = textile", async () => {
    const { user, fake, container } = renderApp("/plateforme?vue=nouvelle", {
      ...adminSession(),
      [`POST ${PLATFORM}`]: json(201, {
        shop: shopSummary({ name: "Tissus Ngaoundéré", profile_code: "textile" }),
        owner_id: "u-9",
        owner_created: true,
        temporary_pin: "482915",
      }),
    });
    const group = await screen.findByRole("radiogroup", { name: "Type de boutique" });
    const names = within(group)
      .getAllByRole("radio")
      .map((radio) => radio.textContent);
    expect(names).toEqual(["Motos et camions", "Prêt-à-porter", "Textile"]);
    for (const radio of within(group).getAllByRole("radio")) {
      expect(radio).toHaveAttribute("aria-checked", "false");
    }
    expect(await axeViolations(container)).toEqual([]);
    await fillShop(user);
    await user.click(screen.getByRole("button", { name: "Ouvrir la boutique" }));
    expect(screen.getByText("Type de boutique : à choisir")).toBeVisible();
    expect(fake.count(`POST ${PLATFORM}`)).toBe(0);
    await user.click(within(group).getByRole("radio", { name: "Textile" }));
    await user.click(screen.getByRole("button", { name: "Ouvrir la boutique" }));
    expect(await screen.findByText("482915")).toBeVisible();
    const sent = fake.calls.find((c) => c.method === "POST" && c.url.endsWith("/platform/shops"));
    expect(sent?.body).toMatchObject({ profile_code: "textile", name: "Tissus Ngaoundéré" });
  });

  it("fiche : type affiché ; changement confirmé, POST /profile puis fiche relue ; axe", async () => {
    const { user, fake, container } = renderApp(SHEET_PATH, {
      ...sheetRoutes(),
      [`POST ${ONE}/profile`]: json(200, shopSummary({ profile_code: "apparel" })),
    });
    expect(await screen.findByText("Type de boutique : Motos et camions")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Changer le type de boutique" }));
    const group = screen.getByRole("radiogroup", { name: "Nouveau type" });
    expect(within(group).queryByRole("radio", { name: "Motos et camions" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Changer le type" }));
    expect(screen.getByText("Choisissez d'abord le nouveau type.")).toBeVisible();
    await user.click(within(group).getByRole("radio", { name: "Prêt-à-porter" }));
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Changer le type" }));
    expect(fake.count(`POST ${ONE}/profile`)).toBe(0); // rien avant la confirmation
    const dialog = screen.getByRole("dialog", { name: "Passer Motos Garoua en Prêt-à-porter ?" });
    await user.click(within(dialog).getByRole("button", { name: "Changer le type" }));
    expect(fake.calls.find((c) => c.url.endsWith("/profile"))?.body).toEqual({
      profile_code: "apparel",
    });
    await screen.findByRole("button", { name: "Changer le type de boutique" });
    expect(fake.count(`GET ${ONE}`)).toBe(2); // fiche relue
  });

  it("PRF-07 : refus PROFILE_CHANGE_BLOCKED → blocages en phrases, la fiche reste", async () => {
    const { user } = renderApp(SHEET_PATH, {
      ...sheetRoutes(),
      [`POST ${ONE}/profile`]: apiError(422, "PROFILE_CHANGE_BLOCKED", "Boutique non vide", {
        blocking: { articles: 1, members: 1 },
        profile: "apparel",
      }),
    });
    await user.click(await screen.findByRole("button", { name: "Changer le type de boutique" }));
    await user.click(screen.getByRole("radio", { name: "Prêt-à-porter" }));
    await user.click(screen.getByRole("button", { name: "Changer le type" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: /Changer/ }));
    expect(
      await screen.findByText(
        /la boutique a déjà 1 article, 1 membre d'un rôle absent du type choisi\./,
      ),
    ).toBeVisible();
    expect(screen.getByRole("heading", { name: "Motos Garoua" })).toBeVisible();
    expect(screen.getByText("Type de boutique : Motos et camions")).toBeVisible();
  });
});

describe("blockingList (PROFILE_CHANGE_BLOCKED)", () => {
  it("singulier, pluriel, ordre servi", () => {
    expect(blockingList({ articles: 3, sales: 1, movements: 2, members: 2 })).toBe(
      "3 articles, 1 vente, 2 mouvements de stock, 2 membres d'un rôle absent du type choisi",
    );
    expect(blockingList({ purchases: 1, expenses: 2, receivables: 1 })).toBe(
      "1 achat, 2 dépenses, 1 créance",
    );
  });

  it("contrat rompu : nature inconnue, nombre invalide, liste au lieu d'objet → erreur", () => {
    expect(() => blockingList({ trucks: 1 })).toThrow(/inconnu/);
    expect(() => blockingList({ articles: 0 })).toThrow(/nombre invalide/);
    expect(() => blockingList(["articles"])).toThrow(/objet/);
    expect(() => blockingList({})).toThrow(/aucun blocage/);
  });
});
